
import requests
import json
import re
import time
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from uuid import uuid4
from pathlib import Path
from openai import OpenAI
import tiktoken  # Make sure to run: pip install tiktoken

# ========== CONFIGURATION ==========
api_key_path = Path("C:/The_GPK/Entry.txt")
with api_key_path.open("r") as f:
    api_key = f.read().strip()

client = OpenAI(api_key=api_key)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_MLS_seasons"

CHUNK_CHAR_LIMIT = 4000
log_file = Path("mls_fact_log.json")
token_log_file = Path("token_usage_log.json")
fact_registry_file = Path("fact_registry.json")  # Persistent store of seen fact hashes

# ========== PROMPT ==========
FACT_EXTRACTION_PROMPT = (
    "You are a soccer expert helping build a competitive trivia game. Given a chunk of text from a Wikipedia article, extract specific, verifiable facts that would make excellent trivia answers.\n\n"
    "Each fact should:\n"
    "- Have a single, clear correct answer.\n"
    "- Be suitable for a 4-option multiple choice question (i.e., allow for 3 plausible but incorrect answer choices).\n"
    "- Focus on meaningful statistics, records, milestones, winners, dates, player or team achievements, transfers, tournaments, and notable events in soccer history.\n\n"
    "Avoid:\n"
    "- General definitions or vague summaries (e.g. 'The Champions League is a competition...') unless tied to a specific year or historical change\n"
    "- Lists of concepts without context or detail\n"
    "- Overly descriptive background that can’t be turned into a clear question\n\n"
    "Return each fact as a standalone bullet point or sentence."
)

# ========== FUNCTIONS ==========

def hash_fact(text):
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()

def extract_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch URL: {url}. Error: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    main_content = soup.find("div", {"class": "mw-parser-output"})
    content = []

    if main_content:
        for element in main_content.find_all(["p", "h2", "h3", "ul", "ol"]):
            text = element.get_text(" ", strip=True)
            if text:
                content.append(text)
        for table in main_content.find_all("table", class_="wikitable"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_text = " | ".join(cell.get_text(" ", strip=True) for cell in cells)
                if row_text:
                    content.append(row_text)

    if not content:
        for table in soup.find_all("table", class_="wikitable"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_text = " | ".join(cell.get_text(" ", strip=True) for cell in cells)
                if row_text:
                    content.append(row_text)

    return "\n".join(content) if content else ""

def chunk_text(text, limit=CHUNK_CHAR_LIMIT):
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 1 <= limit:
            current_chunk += para + "\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            if len(para) > limit:
                para = para[:limit-3] + "..."
            current_chunk = para + "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

def count_tokens(text, model="gpt-4-0125-preview"):
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return int(len(text.split()) * 1.3)

def generate_facts_from_chunk(chunk):
    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_PROMPT},
                {"role": "user", "content": chunk}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        facts_text = response.choices[0].message.content.strip()
        facts = [fact.strip("- ").strip() for fact in facts_text.split("\n") if fact.strip()]
        prompt_tokens = count_tokens(FACT_EXTRACTION_PROMPT + chunk)
        completion_tokens = count_tokens(facts_text)
        return facts, prompt_tokens, completion_tokens
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {e}")

def clean_title_from_url(url):
    path = urlparse(url).path
    return unquote(path.split("/")[-1].replace("_", " "))

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip("_")

# ========== MAIN EXECUTION ==========

def main():
    log = {"success": [], "failures": []}
    token_log = []
    article_data = {}

    if fact_registry_file.exists():
        with fact_registry_file.open("r", encoding="utf-8") as f:
            seen_hashes = set(json.load(f))
    else:
        seen_hashes = set()

    try:
        print(f"Extracting text from: {WIKI_URL}")
        article_text = extract_article_text(WIKI_URL)

        if not article_text.strip():
            raise ValueError("No extractable content found in the article.")

        print(f"Article text length: {len(article_text)} characters")
        chunks = chunk_text(article_text)
        print(f"Split into {len(chunks)} chunks")

        all_facts = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            try:
                facts, prompt_tokens, completion_tokens = generate_facts_from_chunk(chunk)
                all_facts.extend(facts)
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                token_log.append({
                    "chunk": i + 1,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "facts_extracted": len(facts)
                })
                print(f"  Extracted {len(facts)} facts from chunk {i+1}")
                time.sleep(1.5)
            except Exception as e:
                print(f"  Error processing chunk {i+1}: {e}")
                continue

        unique_facts = list(dict.fromkeys(all_facts))

        # Deduplicate based on hash
        new_facts = []
        for fact in unique_facts:
            fact_hash = hash_fact(fact)
            if fact_hash not in seen_hashes:
                new_facts.append(fact)
                seen_hashes.add(fact_hash)

        print(f"Total facts extracted: {len(all_facts)}")
        print(f"Unique facts: {len(unique_facts)}")
        print(f"New unique facts (excluding duplicates): {len(new_facts)}")

        article_title = clean_title_from_url(WIKI_URL)
        article_id_prefix = slugify(article_title)

        structured_facts = [
            {"id": f"{article_id_prefix}_{i+1:03d}", "text": fact}
            for i, fact in enumerate(new_facts)
        ]

        article_data = {
            "source": WIKI_URL,
            "article_title": article_title,
            "facts": structured_facts,
            "extraction_stats": {
                "total_facts": len(all_facts),
                "unique_facts": len(unique_facts),
                "new_unique_facts": len(new_facts),
                "chunks_processed": len(chunks)
            }
        }

        output_file = Path("mls_fact_dump.json")
        unique_output_file = Path(f"{article_id_prefix}_facts.json")

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)

        with unique_output_file.open("w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)

        with fact_registry_file.open("w", encoding="utf-8") as f:
            json.dump(sorted(list(seen_hashes)), f, indent=2)

        log["success"].append(WIKI_URL)

        total_input_cost = total_prompt_tokens / 1000 * 0.01
        total_output_cost = total_completion_tokens / 1000 * 0.03
        total_cost = round(total_input_cost + total_output_cost, 4)

        with token_log_file.open("w", encoding="utf-8") as f:
            json.dump({
                "url": WIKI_URL,
                "article_title": article_title,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "estimated_cost_usd": total_cost,
                "chunk_details": token_log
            }, f, indent=2)

        print(f"Successfully processed article: {article_title}")
        print(f"Output saved to: {output_file} and {unique_output_file}")
        print(f"Estimated cost: ${total_cost}")

    except Exception as e:
        print(f"Error processing article: {e}")
        log["failures"].append({"url": WIKI_URL, "error": str(e)})

    with log_file.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

if __name__ == "__main__":
    main()
