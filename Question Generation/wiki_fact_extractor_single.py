import requests
import json
import re
import time
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from pathlib import Path
from openai import OpenAI
import tiktoken

# ========== CONFIGURATION ==========
# Try multiple possible locations for the API key
possible_api_key_paths = [
    Path("C:/The_GPK/Entry.txt"),
    Path("Entry.txt"),
    Path("api_key.txt")
]

api_key_path = None
for path in possible_api_key_paths:
    if path.exists():
        api_key_path = path
        break

if api_key_path is None:
    print("Error: API key file not found in any of these locations:")
    for path in possible_api_key_paths:
        print(f"  - {path}")
    print("Please create one of these files with your OpenAI API key.")
    exit(1)

try:
    with api_key_path.open("r") as f:
        api_key = f.read().strip()
    
    if not api_key:
        print("Error: API key file is empty.")
        exit(1)
        
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"Error reading API key: {e}")
    exit(1)

CHUNK_CHAR_LIMIT = 4000

# Create output directory if it doesn't exist
output_dir = Path("extracted_facts")
output_dir.mkdir(exist_ok=True)

log_file = output_dir / "mls_fact_log.json"
token_log_file = output_dir / "token_usage_log.json"
fact_registry_file = output_dir / "fact_registry.json"

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
    "- Overly descriptive background that can't be turned into a clear question\n\n"
    "Return each fact as a standalone bullet point or sentence."
)

def hash_fact(text):
    """Generate a hash for a fact to check for duplicates"""
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()

def extract_article_text(url):
    """Extract text content from a Wikipedia article"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch URL: {url}. Error: {e}")

    soup = BeautifulSoup(response.text, "html.parser")
    main_content = soup.find("div", {"class": "mw-parser-output"})
    content = []

    if main_content:
        # Extract main text content
        for element in main_content.find_all(["p", "h2", "h3", "ul", "ol"]):
            text = element.get_text(" ", strip=True)
            if text and len(text) > 20:  # Filter out very short snippets
                content.append(text)
        
        # Extract table content
        for table in main_content.find_all("table", class_="wikitable"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_text = " | ".join(cell.get_text(" ", strip=True) for cell in cells)
                if row_text and len(row_text) > 10:
                    content.append(row_text)

    # Fallback: if no main content found, try to extract any tables
    if not content:
        for table in soup.find_all("table", class_="wikitable"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_text = " | ".join(cell.get_text(" ", strip=True) for cell in cells)
                if row_text and len(row_text) > 10:
                    content.append(row_text)

    return "\n".join(content) if content else ""

def chunk_text(text, limit=CHUNK_CHAR_LIMIT):
    """Split text into chunks of specified character limit"""
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
    """Count tokens in text for the specified model"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback estimation
        return int(len(text.split()) * 1.3)

def generate_facts_from_chunk(chunk):
    """Generate facts from a text chunk using OpenAI API"""
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
    """Extract a clean title from Wikipedia URL"""
    path = urlparse(url).path
    return unquote(path.split("/")[-1].replace("_", " "))

def slugify(text):
    """Convert text to a URL-friendly slug"""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip("_")

def create_sample_urls_file():
    """Create a sample URLs file with common MLS-related Wikipedia pages"""
    sample_urls = [
        "https://en.wikipedia.org/wiki/Major_League_Soccer",
        "https://en.wikipedia.org/wiki/MLS_Cup",
        "https://en.wikipedia.org/wiki/LA_Galaxy",
        "https://en.wikipedia.org/wiki/Seattle_Sounders_FC",
        "https://en.wikipedia.org/wiki/Atlanta_United_FC",
        "https://en.wikipedia.org/wiki/David_Beckham",
        "https://en.wikipedia.org/wiki/Carlos_Vela",
        "https://en.wikipedia.org/wiki/Supporters%27_Shield"
    ]
    
    url_file = Path("MLS_Wikipedia_Links.txt")
    with url_file.open("w", encoding="utf-8") as f:
        for url in sample_urls:
            f.write(url + "\n")
    
    print(f"Created sample file: {url_file}")
    print("You can edit this file to add your own Wikipedia URLs.")
    return url_file

def main():
    """Main function to process Wikipedia articles and extract facts"""
    log = {"success": [], "failures": []}
    token_log = []

    # Load existing fact registry to avoid duplicates
    if fact_registry_file.exists():
        try:
            with fact_registry_file.open("r", encoding="utf-8") as f:
                seen_hashes = set(json.load(f))
        except Exception as e:
            print(f"Warning: Could not load fact registry: {e}")
            seen_hashes = set()
    else:
        seen_hashes = set()

    # Check for URLs file in multiple locations
    possible_url_files = [
        Path("MLS_Wikipedia_Links.txt"),  # Current directory
        Path("Fact_Lists/MLS_Wikipedia_Links.txt"),  # Fact_Lists subdirectory
        Path("C:/Users/aq_pu/Desktop/soccer-trivia-app/Question Generation/Fact_Lists/MLS_Wikipedia_Links.txt")  # Absolute path
    ]
    
    url_file = None
    for file_path in possible_url_files:
        if file_path.exists():
            url_file = file_path
            print(f"Found URLs file at: {url_file}")
            break
    
    if url_file is None:
        print("MLS_Wikipedia_Links.txt not found in any of these locations:")
        for path in possible_url_files:
            print(f"  - {path}")
        print("\nPlease ensure the file exists in one of these locations.")
        return

    # Read URLs from file
    try:
        with url_file.open("r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        print(f"Error reading URLs file: {e}")
        return

    if not urls:
        print("No URLs found in the file.")
        return

    print(f"Found {len(urls)} URLs to process")

    # Process each URL
    for i, WIKI_URL in enumerate(urls, 1):
        print("=" * 80)
        print(f"Processing article {i}/{len(urls)}: {WIKI_URL}")
        
        try:
            # Extract article content
            article_text = extract_article_text(WIKI_URL)
            if not article_text.strip():
                raise ValueError("No extractable content found in the article.")

            print(f"Article text length: {len(article_text)} characters")
            
            # Split into chunks
            chunks = chunk_text(article_text)
            print(f"Split into {len(chunks)} chunks") 

            # Process each chunk
            all_facts = []
            total_prompt_tokens = 0
            total_completion_tokens = 0
            
            for chunk_idx, chunk in enumerate(chunks):
                print(f"Processing chunk {chunk_idx+1}/{len(chunks)}...")
                try:
                    facts, prompt_tokens, completion_tokens = generate_facts_from_chunk(chunk)
                    all_facts.extend(facts)
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    
                    token_log.append({
                        "url": WIKI_URL,
                        "chunk": chunk_idx + 1,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "facts_extracted": len(facts)
                    })
                    
                    print(f"  Extracted {len(facts)} facts from chunk {chunk_idx+1}")
                    time.sleep(1.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"  Error processing chunk {chunk_idx+1}: {e}")
                    continue

            # Remove duplicates within this article
            unique_facts = list(dict.fromkeys(all_facts))
            
            # Filter out facts we've seen before
            new_facts = []
            for fact in unique_facts:
                fact_hash = hash_fact(fact)
                if fact_hash not in seen_hashes:
                    new_facts.append(fact)
                    seen_hashes.add(fact_hash)

            print(f"Total facts extracted: {len(all_facts)}")
            print(f"Unique facts: {len(unique_facts)}")
            print(f"New unique facts (excluding duplicates): {len(new_facts)}")

            # Create structured output
            article_title = clean_title_from_url(WIKI_URL)
            article_id_prefix = slugify(article_title)

            structured_facts = [
                {"id": f"{article_id_prefix}_{j+1:03d}", "text": fact}
                for j, fact in enumerate(new_facts)
            ]

            article_data = {
                "source": WIKI_URL,
                "article_title": article_title,
                "facts": structured_facts,
                "extraction_stats": {
                    "total_facts": len(all_facts),
                    "unique_facts": len(unique_facts),
                    "new_unique_facts": len(new_facts),
                    "chunks_processed": len(chunks),
                    "total_prompt_tokens": total_prompt_tokens,
                    "total_completion_tokens": total_completion_tokens
                }
            }

            # Save outputs
            output_file = output_dir / "mls_fact_dump.json"
            unique_output_file = output_dir / f"{article_id_prefix}_facts.json"

            # Save combined output
            if output_file.exists():
                try:
                    with output_file.open("r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_data.append(article_data)
                    else:
                        existing_data = [existing_data, article_data]
                except Exception:
                    existing_data = [article_data]
            else:
                existing_data = [article_data]

            with output_file.open("w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            # Save individual file
            with unique_output_file.open("w", encoding="utf-8") as f:
                json.dump(article_data, f, indent=2, ensure_ascii=False)

            log["success"].append(WIKI_URL)
            print(f"Successfully processed: {article_title}")

        except Exception as e:
            print(f"Error processing article: {e}")
            log["failures"].append({"url": WIKI_URL, "error": str(e)})

        # Save progress after each article
        with fact_registry_file.open("w", encoding="utf-8") as f:
            json.dump(sorted(list(seen_hashes)), f, indent=2)

    # Save final logs
    with log_file.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    with token_log_file.open("w", encoding="utf-8") as f:
        json.dump(token_log, f, indent=2)

    print("=" * 80)
    print("PROCESSING COMPLETE")
    print(f"✅ {len(log['success'])} articles succeeded")
    print(f"❌ {len(log['failures'])} articles failed")
    
    if log['failures']:
        print("\nFailed articles:")
        for failure in log['failures']:
            print(f"  - {failure['url']}: {failure['error']}")

if __name__ == "__main__":
    main()