# Trivia_Reviewer_Tool_V8_Modified.py
# Enhanced GUI tool to review soccer trivia questions with improved file format handling
# Modified to handle nested array structures like the World Cup questions file

import json
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, simpledialog
from tkinter import ttk
import re
import shutil
from datetime import datetime
import threading
import time

# === SETTINGS ===
DEFAULT_INPUT_FILE = "soc_quest.txt"
ORIGINAL_HARDCODED_PATH = r"C:\soccer_Questions\soc_quest.txt"  # Original hardcoded path
CONFIG_FILE = "trivia_reviewer_config.json"

class TriviaReviewer:
    def __init__(self, master):
        self.master = master
        self.questions = []
        self.filtered_questions = []
        self.index = 0
        self.filter_mode = "all"  # "all", "assigned", "unassigned"
        self.search_term = ""
        self.code_labels = {}
        self.undo_stack = []
        self.redo_stack = []
        self.auto_save_active = True
        self.unsaved_changes = False
        self.input_file_path = ""
        self.output_folder = ""
        
        self.setup_gui()
        self.load_config()
        self.setup_auto_save()
        
        # Try to load questions in this order:
        # 1. Original hardcoded path
        # 2. Default file in current directory
        # 3. Last used file from config
        questions_loaded = False
        
        if os.path.exists(ORIGINAL_HARDCODED_PATH):
            self.load_questions(ORIGINAL_HARDCODED_PATH)
            questions_loaded = True
        elif os.path.exists(DEFAULT_INPUT_FILE):
            self.load_questions(DEFAULT_INPUT_FILE)
            questions_loaded = True
        elif self.input_file_path and os.path.exists(self.input_file_path):
            self.load_questions(self.input_file_path)
            questions_loaded = True
        
        if not questions_loaded:
            self.status_label.config(text="No questions file found. Use File > Open to load questions.")
            messagebox.showinfo("Welcome", 
                               "No questions file found.\n\n" +
                               f"Please use File > Open to select your questions file,\n" +
                               f"or place 'soc_quest.txt' in the current directory.\n\n" +
                               f"Looking for: {ORIGINAL_HARDCODED_PATH}")

    def setup_gui(self):
        self.master.title("Enhanced Trivia Reviewer Tool V8 - World Cup Modified")
        self.master.geometry("1200x800")
        self.master.configure(bg='#f0f0f0')
        
        # Setup keyboard bindings
        self.master.bind('<Left>', lambda e: self.prev_question())
        self.master.bind('<Right>', lambda e: self.next_question())
        self.master.bind('<Control-z>', lambda e: self.undo())
        self.master.bind('<Control-y>', lambda e: self.redo())
        self.master.bind('<Control-f>', lambda e: self.focus_search())
        self.master.bind('<Control-s>', lambda e: self.save_progress())
        self.master.bind('<Control-o>', lambda e: self.open_file())
        
        for i in range(10):
            self.master.bind(str(i), lambda e, x=i: self.assign_code(x))
        
        self.create_menu()
        self.create_toolbar()
        self.create_main_content()
        self.create_status_bar()

    def create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Questions File...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Progress", command=self.save_progress, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export Statistics", command=self.export_statistics)
        file_menu.add_command(label="Create Backup", command=self.create_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Edit Question", command=self.edit_current_question)
        edit_menu.add_command(label="Find", command=self.focus_search, accelerator="Ctrl+F")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Preview Mode", command=self.toggle_preview_mode)
        view_menu.add_command(label="Show Statistics", command=self.show_statistics)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Bulk Assignment", command=self.bulk_assignment)
        tools_menu.add_command(label="Manage Code Labels", command=self.manage_code_labels)
        tools_menu.add_command(label="Validate Questions", command=self.validate_questions)

    def create_toolbar(self):
        toolbar = tk.Frame(self.master, bg='#e0e0e0', height=50)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        # File operations
        tk.Button(toolbar, text="Open", command=self.open_file, width=8).pack(side='left', padx=2)
        tk.Button(toolbar, text="Save", command=self.save_progress, width=8).pack(side='left', padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        # Navigation
        tk.Button(toolbar, text="← Prev", command=self.prev_question, width=8).pack(side='left', padx=2)
        tk.Button(toolbar, text="Next →", command=self.next_question, width=8).pack(side='left', padx=2)
        
        # Jump to question
        tk.Label(toolbar, text="Go to:", bg='#e0e0e0').pack(side='left', padx=5)
        self.jump_var = tk.StringVar()
        jump_entry = tk.Entry(toolbar, textvariable=self.jump_var, width=5)
        jump_entry.pack(side='left', padx=2)
        jump_entry.bind('<Return>', self.jump_to_question)
        
        # Separator
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        # Filter
        tk.Label(toolbar, text="Filter:", bg='#e0e0e0').pack(side='left', padx=5)
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, values=["all", "assigned", "unassigned"], width=10)
        filter_combo.pack(side='left', padx=2)
        filter_combo.bind('<<ComboboxSelected>>', self.apply_filter)
        
        # Search
        tk.Label(toolbar, text="Search:", bg='#e0e0e0').pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=15)
        self.search_entry.pack(side='left', padx=2)
        self.search_entry.bind('<KeyRelease>', self.apply_search)
        
        # Undo/Redo
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        self.undo_btn = tk.Button(toolbar, text="Undo", command=self.undo, width=8, state='disabled')
        self.undo_btn.pack(side='left', padx=2)
        self.redo_btn = tk.Button(toolbar, text="Redo", command=self.redo, width=8, state='disabled')
        self.redo_btn.pack(side='left', padx=2)

    def create_main_content(self):
        # Main content frame
        main_frame = tk.Frame(self.master)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel for question display
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side='left', fill='both', expand=True)
        
        # Progress indicator
        self.progress_frame = tk.Frame(left_panel)
        self.progress_frame.pack(fill='x', pady=5)
        
        self.progress_label = tk.Label(self.progress_frame, text="No questions loaded", font=("Helvetica", 12, "bold"))
        self.progress_label.pack(side='left')
        
        self.assignment_status = tk.Label(self.progress_frame, text="", font=("Helvetica", 10), fg="blue")
        self.assignment_status.pack(side='right')
        
        # Question display with tabs
        self.notebook = ttk.Notebook(left_panel)
        self.notebook.pack(fill='both', expand=True, pady=5)
        
        # JSON view tab
        json_frame = tk.Frame(self.notebook)
        self.notebook.add(json_frame, text="JSON View")
        
        self.json_display = scrolledtext.ScrolledText(json_frame, font=("Courier New", 16), height=20)
        self.json_display.pack(fill='both', expand=True)
        
        # Preview tab
        preview_frame = tk.Frame(self.notebook)
        self.notebook.add(preview_frame, text="Preview")
        
        self.preview_display = scrolledtext.ScrolledText(preview_frame, font=("Helvetica", 11), height=20, wrap=tk.WORD)
        self.preview_display.pack(fill='both', expand=True)
        
        # Right panel for code assignment
        right_panel = tk.Frame(main_frame, width=300, bg='#f8f8f8')
        right_panel.pack(side='right', fill='y', padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Code assignment section
        tk.Label(right_panel, text="Code Assignment", font=("Helvetica", 14, "bold"), bg='#f8f8f8').pack(pady=10)
        
        # Code buttons frame
        codes_frame = tk.Frame(right_panel, bg='#f8f8f8')
        codes_frame.pack(fill='x', padx=10)
        
        self.code_buttons = {}
        for i in range(10):
            btn_frame = tk.Frame(codes_frame, bg='#f8f8f8')
            btn_frame.pack(fill='x', pady=2)
            
            btn = tk.Button(btn_frame, text=f"Code {i}", command=lambda x=i: self.assign_code(x), width=10)
            btn.pack(side='left')
            self.code_buttons[i] = btn
            
            label = tk.Label(btn_frame, text="", font=("Helvetica", 9), bg='#f8f8f8', anchor='w')
            label.pack(side='left', padx=5, fill='x', expand=True)
            
        # Recently used codes
        tk.Label(right_panel, text="Recently Used", font=("Helvetica", 12, "bold"), bg='#f8f8f8').pack(pady=(20, 5))
        self.recent_codes_frame = tk.Frame(right_panel, bg='#f8f8f8')
        self.recent_codes_frame.pack(fill='x', padx=10)
        
        # Code statistics
        tk.Label(right_panel, text="Code Statistics", font=("Helvetica", 12, "bold"), bg='#f8f8f8').pack(pady=(20, 5))
        self.stats_display = scrolledtext.ScrolledText(right_panel, height=8, font=("Helvetica", 9))
        self.stats_display.pack(fill='x', padx=10)
        
        # Action buttons
        action_frame = tk.Frame(right_panel, bg='#f8f8f8')
        action_frame.pack(fill='x', padx=10, pady=20)
        
        tk.Button(action_frame, text="Skip Question", command=self.skip_question, width=15).pack(pady=2)
        tk.Button(action_frame, text="Edit Question", command=self.edit_current_question, width=15).pack(pady=2)
        tk.Button(action_frame, text="Bulk Assign", command=self.bulk_assignment, width=15).pack(pady=2)

    def create_status_bar(self):
        self.status_bar = tk.Frame(self.master, bg='#e0e0e0', height=25)
        self.status_bar.pack(fill='x', side='bottom')
        
        self.status_label = tk.Label(self.status_bar, text="Ready", bg='#e0e0e0', anchor='w')
        self.status_label.pack(side='left', padx=5)
        
        self.auto_save_label = tk.Label(self.status_bar, text="Auto-save: ON", bg='#e0e0e0', fg='green')
        self.auto_save_label.pack(side='right', padx=5)
        
        self.feedback_label = tk.Label(self.status_bar, text="", bg='#e0e0e0', fg='blue')
        self.feedback_label.pack(side='right', padx=20)

    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.code_labels = config.get('code_labels', {})
                    self.input_file_path = config.get('last_file', '')
                    self.output_folder = config.get('output_folder', '')
                    self.update_code_labels_display()
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        config = {
            'code_labels': self.code_labels,
            'last_file': self.input_file_path,
            'output_folder': self.output_folder
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def setup_auto_save(self):
        """Setup auto-save functionality"""
        def auto_save_loop():
            while self.auto_save_active:
                time.sleep(30)  # Auto-save every 30 seconds
                if self.unsaved_changes and self.questions:
                    self.save_progress(show_feedback=False)
        
        self.auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self.auto_save_thread.start()

    def open_file(self):
        """Open and load questions file"""
        file_path = filedialog.askopenfilename(
            title="Select Questions File",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_questions(file_path)

    def flatten_nested_arrays(self, data):
        """Flatten nested arrays into a single array of questions"""
        flattened = []
        
        def process_item(item):
            if isinstance(item, dict):
                # Check if it looks like a question object
                if 'question' in item and 'answer' in item:
                    flattened.append(item)
                else:
                    # If it's a dict but not a question, process its values
                    for value in item.values():
                        process_item(value)
            elif isinstance(item, list):
                # If it's a list, process each item
                for subitem in item:
                    process_item(subitem)
        
        # Process the input data
        if isinstance(data, list):
            for item in data:
                process_item(item)
        else:
            process_item(data)
        
        return flattened

    def detect_file_format(self, raw_text):
        """Detect the format of the input file and return normalized content"""
        lines = raw_text.strip().split('\n')
        
        # Check if it starts with '[' - standard JSON array
        if raw_text.strip().startswith('['):
            return raw_text, "json_array"
        
        # Check for comment-separated JSON objects
        has_comments = any(line.strip().startswith('//') for line in lines)
        has_separate_objects = raw_text.count('{') > 1 and not raw_text.strip().startswith('[')
        
        if has_comments or has_separate_objects:
            return self.convert_commented_format(raw_text), "commented_objects"
        
        # Default fallback
        return raw_text, "unknown"

    def convert_commented_format(self, raw_text):
        """Convert commented format with separate JSON objects to JSON array"""
        lines = raw_text.split('\n')
        
        # Remove comment lines and empty lines
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                filtered_lines.append(line)
        
        # Join back
        cleaned_content = '\n'.join(filtered_lines)
        
        # Find individual JSON objects
        objects = []
        current_object = ""
        brace_count = 0
        in_string = False
        escape_next = False
        
        for char in cleaned_content:
            if escape_next:
                escape_next = False
                current_object += char
                continue
                
            if char == '\\':
                escape_next = True
                current_object += char
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    
            current_object += char
            
            # If we've closed all braces and have content, we have a complete object
            if brace_count == 0 and current_object.strip():
                try:
                    # Try to parse this as JSON to validate
                    parsed = json.loads(current_object.strip())
                    objects.append(parsed)
                    current_object = ""
                except json.JSONDecodeError:
                    # If it fails, keep accumulating
                    pass
        
        # Handle any remaining content
        if current_object.strip():
            try:
                parsed = json.loads(current_object.strip())
                objects.append(parsed)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse remaining content: {e}")
        
        # Return as JSON array string
        return json.dumps(objects, indent=2, ensure_ascii=False)

    def clean_json_content(self, raw_text):
        """Enhanced JSON cleaning to handle multiple formats"""
        # First detect the format
        normalized_content, file_format = self.detect_file_format(raw_text)
        
        if file_format == "commented_objects":
            # Already converted by detect_file_format
            cleaned = normalized_content
        else:
            # Apply original cleaning logic
            cleaned = re.sub(r',\s*\.\.\.\s*', '', normalized_content)
            cleaned = re.sub(r'\.\.\.\s*', '', cleaned)
            cleaned = re.sub(r']\s*\[', ',', cleaned.strip())
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            cleaned = re.sub(r'}\s*{', '},{', cleaned)
        
        return cleaned

    def load_questions(self, file_path):
        """Load and clean questions from file with support for nested arrays"""
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                raw = f.read()

            # Enhanced JSON cleaning with format detection
            cleaned = self.clean_json_content(raw)
            data = json.loads(cleaned)
            
            # NEW: Handle nested arrays by flattening them
            if isinstance(data, list):
                # Check if this is a list of questions or a list of arrays/objects
                flattened_questions = self.flatten_nested_arrays(data)
            else:
                # Single object case
                flattened_questions = self.flatten_nested_arrays([data])
            
            # Validate question structure
            valid_questions = []
            for i, q in enumerate(flattened_questions):
                if self.validate_question_structure(q, i):
                    valid_questions.append(q)
            
            self.questions = valid_questions
            self.input_file_path = file_path
            self.output_folder = os.path.dirname(file_path)
            self.index = 0
            self.apply_filter()
            self.update_display()
            self.update_statistics()
            self.save_config()
            
            self.status_label.config(text=f"Loaded {len(self.questions)} questions from {os.path.basename(file_path)}")
            
            if len(valid_questions) < len(flattened_questions):
                skipped = len(flattened_questions) - len(valid_questions)
                messagebox.showwarning("Import Warning", 
                    f"Loaded {len(valid_questions)} questions successfully.\n"
                    f"Skipped {skipped} questions due to formatting issues.")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Error loading questions: {str(e)}")

    def validate_question_structure(self, question, index):
        """Validate that a question has the required structure"""
        if not isinstance(question, dict):
            print(f"Warning: Question {index + 1} is not a dictionary, skipping...")
            return False
            
        required_fields = ['question', 'answer', 'options', 'category', 'difficulty']
        
        for field in required_fields:
            if field not in question:
                print(f"Warning: Question {index + 1} missing field '{field}', skipping...")
                return False
        
        # Validate that answer is in options
        if question['answer'] not in question['options']:
            print(f"Warning: Question {index + 1} answer '{question['answer']}' not in options {question['options']}, skipping...")
            return False
        
        # Ensure options is a list
        if not isinstance(question['options'], list):
            print(f"Warning: Question {index + 1} options is not a list, skipping...")
            return False
        
        return True

    def apply_filter(self, event=None):
        """Apply current filter to questions"""
        if not self.questions:
            self.filtered_questions = []
            return
        
        filter_mode = self.filter_var.get()
        search_term = self.search_var.get().lower()
        
        filtered = []
        for i, q in enumerate(self.questions):
            # Apply assignment filter
            if filter_mode == "assigned" and 'assigned_code' not in q:
                continue
            elif filter_mode == "unassigned" and 'assigned_code' in q:
                continue
            
            # Apply search filter
            if search_term:
                searchable_text = f"{q.get('question', '')} {q.get('answer', '')} {q.get('category', '')}".lower()
                if search_term not in searchable_text:
                    continue
            
            filtered.append((i, q))
        
        self.filtered_questions = filtered
        
        # Reset index to first filtered question
        if self.filtered_questions:
            self.index = 0
        
        self.update_display()

    def apply_search(self, event=None):
        """Apply search filter"""
        self.apply_filter()

    def focus_search(self):
        """Focus on search entry"""
        self.search_entry.focus()

    def jump_to_question(self, event=None):
        """Jump to specific question number"""
        try:
            question_num = int(self.jump_var.get())
            if 1 <= question_num <= len(self.filtered_questions):
                self.index = question_num - 1
                self.update_display()
                self.jump_var.set("")
            else:
                messagebox.showwarning("Invalid Question", f"Question number must be between 1 and {len(self.filtered_questions)}")
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid question number")

    def get_current_question(self):
        """Get the currently displayed question"""
        if not self.filtered_questions or self.index >= len(self.filtered_questions):
            return None
        return self.filtered_questions[self.index]

    def update_display(self):
        """Update all display elements"""
        if not self.filtered_questions:
            self.progress_label.config(text="No questions to display")
            self.assignment_status.config(text="")
            self.json_display.delete(1.0, tk.END)
            self.preview_display.delete(1.0, tk.END)
            return
        
        current = self.get_current_question()
        if not current:
            return
        
        original_index, q = current
        
        # Update progress
        total_filtered = len(self.filtered_questions)
        assigned_count = sum(1 for _, question in self.filtered_questions if 'assigned_code' in question)
        
        self.progress_label.config(text=f"Question {self.index + 1} of {total_filtered}")
        self.assignment_status.config(
            text=f"Assigned: {assigned_count}/{total_filtered} ({assigned_count/total_filtered*100:.1f}%)"
        )
        
        # Update JSON display
        self.display_json_question(q)
        
        # Update preview display
        self.display_preview_question(q)
        
        # Update code button states
        self.update_code_buttons(q)
        
        # Clear feedback
        self.feedback_label.config(text="")
        
        # Update undo/redo buttons
        self.update_undo_redo_buttons()

    def display_json_question(self, q):
        """Display question in JSON format with compact formatting"""
        display_text = ""
        display_text += f"\"question\": \"{q['question']}\",\n"
        display_text += f"\"answer\": \"{q['answer']}\",\n"
        options_str = ', '.join([f'"{opt}"' for opt in q['options']])
        display_text += f"\"options\": [{options_str}],\n"
        
        # Handle category field (could be string or list)
        category = q.get('category', '')
        if isinstance(category, list):
            category_str = ', '.join([f'"{cat}"' for cat in category])
            display_text += f"\"category\": [{category_str}],\n"
        else:
            display_text += f"\"category\": \"{category}\",\n"
        
        # Handle subcategories field
        subcategories = q.get('subcategories', [])
        if subcategories:
            subcategories_str = ', '.join([f'"{sub}"' for sub in subcategories])
            display_text += f"\"subcategories\": [{subcategories_str}],\n"
        
        display_text += f"\"difficulty\": \"{q['difficulty']}\""
        
        if 'assigned_code' in q:
            display_text += f",\n\"assigned_code\": {q['assigned_code']}"
        
        self.json_display.delete(1.0, tk.END)
        self.json_display.insert(tk.END, display_text)

    def display_preview_question(self, q):
        """Display question in user-friendly preview format"""
        preview_text = ""
        preview_text += f"QUESTION: {q['question']}\n\n"
        
        preview_text += "OPTIONS:\n"
        for i, option in enumerate(q['options'], 1):
            marker = "✓" if option == q['answer'] else " "
            preview_text += f"{marker} {i}. {option}\n"
        
        preview_text += f"\nCORRECT ANSWER: {q['answer']}\n\n"
        
        # Handle category display
        category = q.get('category', '')
        if isinstance(category, list):
            preview_text += f"CATEGORY: {', '.join(category)}\n"
        else:
            preview_text += f"CATEGORY: {category}\n"
        
        # Handle subcategories
        subcategories = q.get('subcategories', [])
        if subcategories:
            preview_text += f"SUBCATEGORIES: {', '.join(subcategories)}\n"
        
        preview_text += f"DIFFICULTY: {q['difficulty']}\n"
        
        if 'assigned_code' in q:
            code_label = self.code_labels.get(str(q['assigned_code']), f"Code {q['assigned_code']}")
            preview_text += f"ASSIGNED TO: {code_label}\n"
        
        self.preview_display.delete(1.0, tk.END)
        self.preview_display.insert(tk.END, preview_text)

    def update_code_buttons(self, q):
        """Update code button states"""
        current_code = q.get('assigned_code')
        
        for i, btn in self.code_buttons.items():
            if i == current_code:
                btn.config(bg='lightgreen', relief='sunken')
            else:
                btn.config(bg='SystemButtonFace', relief='raised')

    def update_code_labels_display(self):
        """Update code button labels"""
        for i in range(10):
            if hasattr(self, 'code_buttons'):
                label_text = self.code_labels.get(str(i), "")
                # Find the label widget next to the button
                btn_frame = self.code_buttons[i].master
                for widget in btn_frame.winfo_children():
                    if isinstance(widget, tk.Label) and widget != self.code_buttons[i]:
                        widget.config(text=label_text)
                        break

    def next_question(self):
        """Navigate to next question"""
        if self.index < len(self.filtered_questions) - 1:
            self.index += 1
            self.update_display()

    def prev_question(self):
        """Navigate to previous question"""
        if self.index > 0:
            self.index -= 1
            self.update_display()

    def skip_question(self):
        """Skip current question and mark for later review"""
        current = self.get_current_question()
        if current:
            original_index, q = current
            q['skipped'] = True
            self.unsaved_changes = True
            self.next_question()

    def assign_code(self, code):
        """Assign code to current question"""
        current = self.get_current_question()
        if not current:
            return
        
        original_index, q = current
        old_code = q.get('assigned_code')
        
        # Save state for undo
        self.save_undo_state(original_index, 'assign_code', old_code, code)
        
        # Remove from previous code file if it exists
        if old_code is not None:
            self.remove_from_code_file(q, old_code)
        
        # Assign new code and save
        q['assigned_code'] = code
        self.save_to_code_file(q, code)
        
        self.unsaved_changes = True
        self.update_display()
        self.update_statistics()
        
        code_label = self.code_labels.get(str(code), f"Code {code}")
        self.feedback_label.config(text=f"✅ Assigned to {code_label}")
        
        # Auto-advance to next unassigned question
        self.next_unassigned_question()

    def next_unassigned_question(self):
        """Move to next unassigned question"""
        start_index = self.index + 1
        for i in range(start_index, len(self.filtered_questions)):
            _, q = self.filtered_questions[i]
            if 'assigned_code' not in q:
                self.index = i
                self.update_display()
                return
        
        # If no unassigned questions found after current, just move to next
        self.next_question()

    def save_to_code_file(self, question, code):
        """Save question to appropriate code file"""
        if not self.output_folder:
            return
        
        output_path = os.path.join(self.output_folder, f"code_{code}.json")
        
        try:
            # Check if we can write to the directory
            if not os.access(self.output_folder, os.W_OK):
                raise PermissionError(f"No write permission to directory: {self.output_folder}")
            
            # Load existing questions
            existing = []
            if os.path.exists(output_path):
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            existing = json.loads(content)
                            if not isinstance(existing, list):
                                print(f"Warning: code_{code}.json was not a list, creating new list")
                                existing = []
                except json.JSONDecodeError as e:
                    print(f"Warning: code_{code}.json was corrupted, backing up and creating new file")
                    # Backup corrupted file
                    backup_path = output_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(output_path, backup_path)
                    existing = []
                except Exception as e:
                    print(f"Warning: Could not read code_{code}.json: {e}")
                    existing = []
            
            # Check for duplicates (improved logic)
            question_key = (question['question'], question['answer'])
            existing = [q for q in existing if (q.get('question'), q.get('answer')) != question_key]
            
            # Add new question
            existing.append(question)
            
            # Create temporary file first to avoid corruption
            temp_path = output_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Custom formatting: nice indentation but arrays on single lines
                json_str = json.dumps(existing, indent=2, ensure_ascii=False)
                # Convert multi-line arrays to single lines
                json_str = re.sub(r'\[\s*\n\s*(".*?")\s*(?:,\s*\n\s*(".*?"))*\s*\n\s*\]', 
                                  lambda m: '[' + ', '.join(re.findall(r'".*?"', m.group(0))) + ']', 
                                  json_str)
                f.write(json_str)
            
            # Atomically replace the original file
            if os.path.exists(output_path):
                if os.name == 'nt':  # Windows
                    os.replace(temp_path, output_path)
                else:  # Unix/Linux/Mac
                    os.rename(temp_path, output_path)
            else:
                os.rename(temp_path, output_path)
                
        except PermissionError as e:
            messagebox.showerror("Permission Error", f"Cannot write to code_{code}.json: {str(e)}\n\nTry running as administrator or check file permissions.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving to code_{code}.json: {str(e)}\n\nFile path: {output_path}")
            # Clean up temp file if it exists
            temp_path = output_path + ".tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def remove_from_code_file(self, question, code):
        """Remove question from code file"""
        if not self.output_folder:
            return
        
        output_path = os.path.join(self.output_folder, f"code_{code}.json")
        
        if not os.path.exists(output_path):
            return
        
        try:
            # Check if we can write to the file
            if not os.access(output_path, os.W_OK):
                raise PermissionError(f"No write permission to file: {output_path}")
            
            existing = []
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        existing = json.load(f)
                        if not isinstance(existing, list):
                            return
            except json.JSONDecodeError as e:
                print(f"Warning: code_{code}.json was corrupted during removal: {e}")
                return
            except Exception as e:
                print(f"Warning: Could not read code_{code}.json for removal: {e}")
                return
            
            # Remove question (improved logic)
            question_key = (question['question'], question['answer'])
            original_count = len(existing)
            existing = [q for q in existing if (q.get('question'), q.get('answer')) != question_key]
            
            # Only save if something was actually removed
            if len(existing) < original_count:
                # Create temporary file first
                temp_path = output_path + ".tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    # Custom formatting: nice indentation but arrays on single lines
                    json_str = json.dumps(existing, indent=2, ensure_ascii=False)
                    # Convert multi-line arrays to single lines
                    json_str = re.sub(r'\[\s*\n\s*(".*?")\s*(?:,\s*\n\s*(".*?"))*\s*\n\s*\]', 
                                      lambda m: '[' + ', '.join(re.findall(r'".*?"', m.group(0))) + ']', 
                                      json_str)
                    f.write(json_str)
                
                # Atomically replace the original file
                if os.name == 'nt':  # Windows
                    os.replace(temp_path, output_path)
                else:  # Unix/Linux/Mac
                    os.rename(temp_path, output_path)
                
        except PermissionError as e:
            messagebox.showerror("Permission Error", f"Cannot modify code_{code}.json: {str(e)}\n\nTry running as administrator or check file permissions.")
        except Exception as e:
            messagebox.showerror("Remove Error", f"Error removing from code_{code}.json: {str(e)}\n\nFile path: {output_path}")
            # Clean up temp file if it exists
            temp_path = output_path + ".tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def save_undo_state(self, question_index, action, old_value, new_value):
        """Save state for undo functionality"""
        state = {
            'question_index': question_index,
            'action': action,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.now()
        }
        
        self.undo_stack.append(state)
        
        # Limit undo stack size
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        
        # Clear redo stack
        self.redo_stack.clear()

    def undo(self):
        """Undo last action"""
        if not self.undo_stack:
            return
        
        state = self.undo_stack.pop()
        self.redo_stack.append(state)
        
        # Find the question
        question_index = state['question_index']
        question = self.questions[question_index]
        
        if state['action'] == 'assign_code':
            old_code = state['old_value']
            
            # Remove from current code file
            if 'assigned_code' in question:
                self.remove_from_code_file(question, question['assigned_code'])
            
            # Restore old assignment
            if old_code is not None:
                question['assigned_code'] = old_code
                self.save_to_code_file(question, old_code)
            else:
                question.pop('assigned_code', None)
        
        self.unsaved_changes = True
        self.apply_filter()
        self.update_display()
        self.update_statistics()

    def redo(self):
        """Redo last undone action"""
        if not self.redo_stack:
            return
        
        state = self.redo_stack.pop()
        self.undo_stack.append(state)
        
        # Find the question
        question_index = state['question_index']
        question = self.questions[question_index]
        
        if state['action'] == 'assign_code':
            new_code = state['new_value']
            
            # Remove from current code file
            if 'assigned_code' in question:
                self.remove_from_code_file(question, question['assigned_code'])
            
            # Apply new assignment
            question['assigned_code'] = new_code
            self.save_to_code_file(question, new_code)
        
        self.unsaved_changes = True
        self.apply_filter()
        self.update_display()
        self.update_statistics()

    def update_undo_redo_buttons(self):
        """Update undo/redo button states"""
        self.undo_btn.config(state='normal' if self.undo_stack else 'disabled')
        self.redo_btn.config(state='normal' if self.redo_stack else 'disabled')

    def update_statistics(self):
        """Update code statistics display"""
        if not self.questions:
            self.stats_display.delete(1.0, tk.END)
            return
        
        stats = {}
        for q in self.questions:
            code = q.get('assigned_code')
            if code is not None:
                if code not in stats:
                    stats[code] = 0
                stats[code] += 1
        
        # Display statistics
        self.stats_display.delete(1.0, tk.END)
        
        total_assigned = sum(stats.values())
        total_questions = len(self.questions)
        unassigned = total_questions - total_assigned
        
        stats_text = f"Total Questions: {total_questions}\n"
        stats_text += f"Assigned: {total_assigned}\n"
        stats_text += f"Unassigned: {unassigned}\n\n"
        
        for code in sorted(stats.keys()):
            label = self.code_labels.get(str(code), f"Code {code}")
            stats_text += f"{label}: {stats[code]}\n"
        
        self.stats_display.insert(tk.END, stats_text)

    def save_progress(self, show_feedback=True):
        """Save current progress"""
        if not self.questions or not self.output_folder:
            return
        
        try:
            # Save main questions file with assignments
            progress_file = os.path.join(self.output_folder, "progress_backup.json")
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.questions, f, indent=2, ensure_ascii=False)
            
            self.unsaved_changes = False
            if show_feedback:
                self.feedback_label.config(text="✅ Progress saved")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving progress: {str(e)}")

    def create_backup(self):
        """Create backup of all files"""
        if not self.output_folder:
            messagebox.showwarning("No Output Folder", "No output folder selected")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(self.output_folder, f"backup_{timestamp}")
            os.makedirs(backup_folder, exist_ok=True)
            
            # Copy all code files
            for i in range(10):
                code_file = os.path.join(self.output_folder, f"code_{i}.json")
                if os.path.exists(code_file):
                    shutil.copy2(code_file, backup_folder)
            
            # Copy progress file
            progress_file = os.path.join(self.output_folder, "progress_backup.json")
            if os.path.exists(progress_file):
                shutil.copy2(progress_file, backup_folder)
            
            messagebox.showinfo("Backup Created", f"Backup created in: {backup_folder}")
            
        except Exception as e:
            messagebox.showerror("Backup Error", f"Error creating backup: {str(e)}")

    def export_statistics(self):
        """Export detailed statistics"""
        if not self.questions:
            messagebox.showwarning("No Data", "No questions loaded")
            return
        
        file_path = filedialog.asksavename(
            title="Export Statistics",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            stats = {
                'total_questions': len(self.questions),
                'assigned': 0,
                'unassigned': 0,
                'by_code': {},
                'by_category': {},
                'by_difficulty': {}
            }
            
            for q in self.questions:
                code = q.get('assigned_code')
                category = q.get('category', 'Unknown')
                difficulty = q.get('difficulty', 'Unknown')
                
                # Handle category field (could be string or list)
                if isinstance(category, list):
                    category = ', '.join(category)
                
                if code is not None:
                    stats['assigned'] += 1
                    if code not in stats['by_code']:
                        stats['by_code'][code] = 0
                    stats['by_code'][code] += 1
                else:
                    stats['unassigned'] += 1
                
                if category not in stats['by_category']:
                    stats['by_category'][category] = 0
                stats['by_category'][category] += 1
                
                if difficulty not in stats['by_difficulty']:
                    stats['by_difficulty'][difficulty] = 0
                stats['by_difficulty'][difficulty] += 1
            
            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2, ensure_ascii=False)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("TRIVIA QUESTIONS STATISTICS\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Total Questions: {stats['total_questions']}\n")
                    f.write(f"Assigned: {stats['assigned']}\n")
                    f.write(f"Unassigned: {stats['unassigned']}\n\n")
                    
                    f.write("BY CODE:\n")
                    for code, count in sorted(stats['by_code'].items()):
                        label = self.code_labels.get(str(code), f"Code {code}")
                        f.write(f"  {label}: {count}\n")
                    
                    f.write("\nBY CATEGORY:\n")
                    for category, count in sorted(stats['by_category'].items()):
                        f.write(f"  {category}: {count}\n")
                    
                    f.write("\nBY DIFFICULTY:\n")
                    for difficulty, count in sorted(stats['by_difficulty'].items()):
                        f.write(f"  {difficulty}: {count}\n")
            
            messagebox.showinfo("Export Complete", f"Statistics exported to: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting statistics: {str(e)}")

    def show_statistics(self):
        """Show detailed statistics in popup window"""
        if not self.questions:
            messagebox.showwarning("No Data", "No questions loaded")
            return
        
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Detailed Statistics")
        stats_window.geometry("600x400")
        
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Overall stats
        overall_frame = tk.Frame(notebook)
        notebook.add(overall_frame, text="Overall")
        
        overall_text = scrolledtext.ScrolledText(overall_frame, font=("Courier New", 10))
        overall_text.pack(fill='both', expand=True)
        
        # Category stats
        category_frame = tk.Frame(notebook)
        notebook.add(category_frame, text="By Category")
        
        category_text = scrolledtext.ScrolledText(category_frame, font=("Courier New", 10))
        category_text.pack(fill='both', expand=True)
        
        # Difficulty stats
        difficulty_frame = tk.Frame(notebook)
        notebook.add(difficulty_frame, text="By Difficulty")
        
        difficulty_text = scrolledtext.ScrolledText(difficulty_frame, font=("Courier New", 10))
        difficulty_text.pack(fill='both', expand=True)
        
        # Calculate and display stats
        self.calculate_detailed_stats(overall_text, category_text, difficulty_text)

    def calculate_detailed_stats(self, overall_text, category_text, difficulty_text):
        """Calculate and display detailed statistics"""
        stats = {
            'by_code': {},
            'by_category': {},
            'by_difficulty': {},
            'by_category_code': {},
            'by_difficulty_code': {}
        }
        
        total_assigned = 0
        
        for q in self.questions:
            code = q.get('assigned_code')
            category = q.get('category', 'Unknown')
            difficulty = q.get('difficulty', 'Unknown')
            
            # Handle category field (could be string or list)
            if isinstance(category, list):
                category = ', '.join(category)
            
            if code is not None:
                total_assigned += 1
                
                # By code
                if code not in stats['by_code']:
                    stats['by_code'][code] = 0
                stats['by_code'][code] += 1
                
                # By category and code
                if category not in stats['by_category_code']:
                    stats['by_category_code'][category] = {}
                if code not in stats['by_category_code'][category]:
                    stats['by_category_code'][category][code] = 0
                stats['by_category_code'][category][code] += 1
                
                # By difficulty and code
                if difficulty not in stats['by_difficulty_code']:
                    stats['by_difficulty_code'][difficulty] = {}
                if code not in stats['by_difficulty_code'][difficulty]:
                    stats['by_difficulty_code'][difficulty][code] = 0
                stats['by_difficulty_code'][difficulty][code] += 1
            
            # Overall category and difficulty
            if category not in stats['by_category']:
                stats['by_category'][category] = 0
            stats['by_category'][category] += 1
            
            if difficulty not in stats['by_difficulty']:
                stats['by_difficulty'][difficulty] = 0
            stats['by_difficulty'][difficulty] += 1
        
        # Display overall stats
        overall_text.delete(1.0, tk.END)
        text = f"OVERALL STATISTICS\n{'='*50}\n\n"
        text += f"Total Questions: {len(self.questions)}\n"
        text += f"Assigned: {total_assigned} ({total_assigned/len(self.questions)*100:.1f}%)\n"
        text += f"Unassigned: {len(self.questions) - total_assigned}\n\n"
        
        text += "ASSIGNMENTS BY CODE:\n"
        for code in sorted(stats['by_code'].keys()):
            label = self.code_labels.get(str(code), f"Code {code}")
            count = stats['by_code'][code]
            text += f"  {label}: {count} ({count/total_assigned*100:.1f}%)\n"
        
        overall_text.insert(tk.END, text)
        
        # Display category stats
        category_text.delete(1.0, tk.END)
        text = f"STATISTICS BY CATEGORY\n{'='*50}\n\n"
        
        for category in sorted(stats['by_category'].keys()):
            total_cat = stats['by_category'][category]
            text += f"{category}: {total_cat} questions\n"
            
            if category in stats['by_category_code']:
                for code in sorted(stats['by_category_code'][category].keys()):
                    label = self.code_labels.get(str(code), f"Code {code}")
                    count = stats['by_category_code'][category][code]
                    text += f"  → {label}: {count}\n"
            text += "\n"
        
        category_text.insert(tk.END, text)
        
        # Display difficulty stats
        difficulty_text.delete(1.0, tk.END)
        text = f"STATISTICS BY DIFFICULTY\n{'='*50}\n\n"
        
        for difficulty in sorted(stats['by_difficulty'].keys()):
            total_diff = stats['by_difficulty'][difficulty]
            text += f"{difficulty}: {total_diff} questions\n"
            
            if difficulty in stats['by_difficulty_code']:
                for code in sorted(stats['by_difficulty_code'][difficulty].keys()):
                    label = self.code_labels.get(str(code), f"Code {code}")
                    count = stats['by_difficulty_code'][difficulty][code]
                    text += f"  → {label}: {count}\n"
            text += "\n"
        
        difficulty_text.insert(tk.END, text)

    def manage_code_labels(self):
        """Manage code labels"""
        labels_window = tk.Toplevel(self.master)
        labels_window.title("Manage Code Labels")
        labels_window.geometry("500x400")
        
        # Instructions
        tk.Label(labels_window, text="Set descriptive labels for each code:", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Code label entries
        entries_frame = tk.Frame(labels_window)
        entries_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        label_vars = {}
        for i in range(10):
            frame = tk.Frame(entries_frame)
            frame.pack(fill='x', pady=2)
            
            tk.Label(frame, text=f"Code {i}:", width=8).pack(side='left')
            
            var = tk.StringVar(value=self.code_labels.get(str(i), ""))
            entry = tk.Entry(frame, textvariable=var, width=40)
            entry.pack(side='left', padx=5, fill='x', expand=True)
            
            label_vars[i] = var
        
        # Buttons
        button_frame = tk.Frame(labels_window)
        button_frame.pack(pady=20)
        
        def save_labels():
            for i, var in label_vars.items():
                label_text = var.get().strip()
                if label_text:
                    self.code_labels[str(i)] = label_text
                else:
                    self.code_labels.pop(str(i), None)
            
            self.update_code_labels_display()
            self.save_config()
            labels_window.destroy()
            messagebox.showinfo("Success", "Code labels updated")
        
        tk.Button(button_frame, text="Save", command=save_labels, width=10).pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", command=labels_window.destroy, width=10).pack(side='left', padx=5)

    def bulk_assignment(self):
        """Bulk assign multiple questions to same code"""
        if not self.questions:
            messagebox.showwarning("No Data", "No questions loaded")
            return
        
        bulk_window = tk.Toplevel(self.master)
        bulk_window.title("Bulk Assignment")
        bulk_window.geometry("600x500")
        
        # Instructions
        tk.Label(bulk_window, text="Select questions to assign to the same code:", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Question list with checkboxes
        list_frame = tk.Frame(bulk_window)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create checkboxes for questions
        question_vars = {}
        for i, q in enumerate(self.questions):
            if 'assigned_code' not in q:  # Only show unassigned questions
                var = tk.BooleanVar()
                frame = tk.Frame(scrollable_frame)
                frame.pack(fill='x', pady=1)
                
                checkbox = tk.Checkbutton(frame, variable=var, text=f"{i+1}. {q['question'][:80]}...", 
                                        wraplength=500, anchor='w', justify='left')
                checkbox.pack(fill='x')
                
                question_vars[i] = var
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Code selection and action buttons
        bottom_frame = tk.Frame(bulk_window)
        bottom_frame.pack(fill='x', padx=20, pady=10)
        
        tk.Label(bottom_frame, text="Assign to code:").pack(side='left')
        
        code_var = tk.StringVar(value="0")
        code_combo = ttk.Combobox(bottom_frame, textvariable=code_var, 
                                values=[f"{i} - {self.code_labels.get(str(i), f'Code {i}')}" for i in range(10)],
                                width=30)
        code_combo.pack(side='left', padx=5)
        
        def bulk_assign():
            selected_indices = [i for i, var in question_vars.items() if var.get()]
            if not selected_indices:
                messagebox.showwarning("No Selection", "Please select at least one question")
                return
            
            try:
                code = int(code_var.get().split()[0])
                for i in selected_indices:
                    self.questions[i]['assigned_code'] = code
                    self.save_to_code_file(self.questions[i], code)
                
                self.unsaved_changes = True
                self.apply_filter()
                self.update_display()
                self.update_statistics()
                
                bulk_window.destroy()
                messagebox.showinfo("Success", f"Assigned {len(selected_indices)} questions to code {code}")
                
            except ValueError:
                messagebox.showerror("Error", "Invalid code selection")
        
        tk.Button(bottom_frame, text="Assign Selected", command=bulk_assign, width=15).pack(side='right', padx=5)
        tk.Button(bottom_frame, text="Cancel", command=bulk_window.destroy, width=10).pack(side='right')

    def edit_current_question(self):
        """Edit the current question"""
        current = self.get_current_question()
        if not current:
            return
        
        original_index, q = current
        
        edit_window = tk.Toplevel(self.master)
        edit_window.title("Edit Question")
        edit_window.geometry("600x500")
        
        # Question field
        tk.Label(edit_window, text="Question:", font=("Helvetica", 10, "bold")).pack(anchor='w', padx=10, pady=(10,0))
        question_text = scrolledtext.ScrolledText(edit_window, height=3, wrap=tk.WORD)
        question_text.pack(fill='x', padx=10, pady=5)
        question_text.insert(tk.END, q['question'])
        
        # Answer field
        tk.Label(edit_window, text="Answer:", font=("Helvetica", 10, "bold")).pack(anchor='w', padx=10, pady=(10,0))
        answer_var = tk.StringVar(value=q['answer'])
        answer_entry = tk.Entry(edit_window, textvariable=answer_var)
        answer_entry.pack(fill='x', padx=10, pady=5)
        
        # Options field
        tk.Label(edit_window, text="Options (one per line):", font=("Helvetica", 10, "bold")).pack(anchor='w', padx=10, pady=(10,0))
        options_text = scrolledtext.ScrolledText(edit_window, height=4, wrap=tk.WORD)
        options_text.pack(fill='x', padx=10, pady=5)
        options_text.insert(tk.END, '\n'.join(q['options']))
        
        # Category field
        tk.Label(edit_window, text="Category:", font=("Helvetica", 10, "bold")).pack(anchor='w', padx=10, pady=(10,0))
        category = q.get('category', '')
        if isinstance(category, list):
            category = ', '.join(category)
        category_var = tk.StringVar(value=category)
        category_entry = tk.Entry(edit_window, textvariable=category_var)
        category_entry.pack(fill='x', padx=10, pady=5)
        
        # Difficulty field
        tk.Label(edit_window, text="Difficulty:", font=("Helvetica", 10, "bold")).pack(anchor='w', padx=10, pady=(10,0))
        difficulty_var = tk.StringVar(value=q['difficulty'])
        difficulty_combo = ttk.Combobox(edit_window, textvariable=difficulty_var, 
                                      values=["easy", "hard"], width=20)
        difficulty_combo.pack(anchor='w', padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(edit_window)
        button_frame.pack(pady=20)
        
        def save_changes():
            try:
                new_question = question_text.get(1.0, tk.END).strip()
                new_answer = answer_var.get().strip()
                new_options = [opt.strip() for opt in options_text.get(1.0, tk.END).strip().split('\n') if opt.strip()]
                new_category = category_var.get().strip()
                new_difficulty = difficulty_var.get().strip()
                
                if not all([new_question, new_answer, new_options, new_category, new_difficulty]):
                    messagebox.showerror("Error", "All fields are required")
                    return
                
                if new_answer not in new_options:
                    messagebox.showerror("Error", "Answer must be one of the options")
                    return
                
                # Update question
                q['question'] = new_question
                q['answer'] = new_answer
                q['options'] = new_options
                q['category'] = new_category
                q['difficulty'] = new_difficulty
                
                # Update code files if question is assigned
                if 'assigned_code' in q:
                    self.save_to_code_file(q, q['assigned_code'])
                
                self.unsaved_changes = True
                self.update_display()
                
                edit_window.destroy()
                messagebox.showinfo("Success", "Question updated successfully")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving changes: {str(e)}")
        
        tk.Button(button_frame, text="Save Changes", command=save_changes, width=15).pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", command=edit_window.destroy, width=10).pack(side='left', padx=5)

    def validate_questions(self):
        """Validate all questions for completeness and consistency"""
        if not self.questions:
            messagebox.showwarning("No Data", "No questions loaded")
            return
        
        issues = []
        
        for i, q in enumerate(self.questions):
            question_issues = []
            
            # Check required fields
            required_fields = ['question', 'answer', 'options', 'category', 'difficulty']
            for field in required_fields:
                if field not in q or not q[field]:
                    question_issues.append(f"Missing {field}")
            
            # Check if answer is in options
            if 'answer' in q and 'options' in q:
                if q['answer'] not in q['options']:
                    question_issues.append("Answer not in options")
            
            # Check options count
            if 'options' in q and len(q['options']) < 2:
                question_issues.append("Less than 2 options")
            
            # Check for duplicates in options
            if 'options' in q and len(q['options']) != len(set(q['options'])):
                question_issues.append("Duplicate options")
            
            if question_issues:
                issues.append(f"Question {i+1}: {', '.join(question_issues)}")
        
        # Show validation results
        validation_window = tk.Toplevel(self.master)
        validation_window.title("Validation Results")
        validation_window.geometry("600x400")
        
        if issues:
            tk.Label(validation_window, text=f"Found {len(issues)} issues:", 
                    font=("Helvetica", 12, "bold"), fg="red").pack(pady=10)
            
            issues_text = scrolledtext.ScrolledText(validation_window)
            issues_text.pack(fill='both', expand=True, padx=10, pady=10)
            
            for issue in issues:
                issues_text.insert(tk.END, issue + "\n")
        else:
            tk.Label(validation_window, text="No issues found! All questions are valid.", 
                    font=("Helvetica", 12, "bold"), fg="green").pack(pady=50)
        
        tk.Button(validation_window, text="Close", command=validation_window.destroy).pack(pady=10)

    def toggle_preview_mode(self):
        """Toggle between JSON and preview mode"""
        current_tab = self.notebook.index(self.notebook.select())
        next_tab = 1 - current_tab
        self.notebook.select(next_tab)

    def on_closing(self):
        """Handle application closing"""
        if self.unsaved_changes:
            result = messagebox.askyesnocancel("Unsaved Changes", 
                                             "You have unsaved changes. Save before closing?")
            if result is True:
                self.save_progress()
            elif result is None:
                return
        
        self.auto_save_active = False
        self.save_config()
        self.master.destroy()

# === MAIN ===
if __name__ == '__main__':
    def main():
        root = tk.Tk()
        app = TriviaReviewer(root)
        
        # Handle window closing
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        root.mainloop()
    
    main()