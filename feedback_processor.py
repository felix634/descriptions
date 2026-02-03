"""
Feedback Processor
Compares AI descriptions with your corrections and updates training data.

USAGE:
1. After running descriptions.py, open completed_analysis.xlsx
2. Review the 'AI_Description' column
3. Add your corrections in 'Your_Correction' column
4. Save the Excel file
5. Run this script: python feedback_processor.py
"""
import pandas as pd
import json
import os
from datetime import datetime
from config import OUTPUT_FILE


def load_json_file(filepath: str) -> list:
    """Load JSON file or return empty list."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_json_file(filepath: str, data: list):
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_benchmark_name_from_file(instructions_file: str = "task_instructions.txt") -> str:
    """Extract benchmark name from current instructions."""
    if not os.path.exists(instructions_file):
        return "general"
    
    with open(instructions_file, 'r', encoding='utf-8') as f:
        content = f.read().lower()
    
    words = content.split()[:20]
    stop_words = {'we', 'are', 'the', 'a', 'an', 'for', 'of', 'to', 'in', 'on', 'is', 
                  'please', 'write', 'analyzing', 'looking', 'describe', 'description'}
    key_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    return '_'.join(key_words[:3]) if key_words else 'general'


def process_feedback():
    print("=" * 60)
    print("   FEEDBACK PROCESSOR")
    print("=" * 60)
    
    # 1. Load the output Excel file
    if not os.path.exists(OUTPUT_FILE):
        print(f"❌ Error: {OUTPUT_FILE} not found. Run descriptions.py first.")
        return
    
    try:
        df = pd.read_excel(OUTPUT_FILE)
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return
    
    # 2. Check for required columns
    required_cols = ['URL', 'AI_Description', 'Your_Correction']
    for col in required_cols:
        if col not in df.columns:
            print(f"❌ Error: Missing column '{col}'")
            return
    
    # 3. Find rows with corrections
    corrections = df[df['Your_Correction'].notna() & (df['Your_Correction'] != '')]
    
    if len(corrections) == 0:
        print("\n📝 No corrections found in 'Your_Correction' column.")
        print("   Add your corrections and run this script again.")
        return
    
    print(f"\n✅ Found {len(corrections)} corrections to process\n")
    
    # 4. Get current benchmark name and instructions
    benchmark_name = extract_benchmark_name_from_file()
    instructions = ""
    visual_check = ""
    if os.path.exists("task_instructions.txt"):
        with open("task_instructions.txt", 'r', encoding='utf-8') as f:
            instructions = f.read().strip()
    
    # 5. Load existing training data
    training_file = f"learning/training_{benchmark_name}.json"
    training_data = load_json_file(training_file)
    
    # Load feedback log
    feedback_log = load_json_file("learning/feedback_log.json")
    
    # 6. Process each correction
    new_examples = 0
    for _, row in corrections.iterrows():
        url = row['URL']
        ai_desc = row['AI_Description']
        human_desc = row['Your_Correction']
        html_snippet = row.get('Html_Snippet', '')
        
        # Skip if AI and human are identical
        if ai_desc.strip() == human_desc.strip():
            continue
        
        # Create training record
        training_record = {
            "benchmark_context": instructions[:200],
            "url": url,
            "html_snippet": html_snippet,
            "ai_description": ai_desc,
            "human_description": human_desc,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to training data (check for duplicates)
        if not any(t.get('url') == url and t.get('benchmark_context') == training_record['benchmark_context'] 
                   for t in training_data):
            training_data.append(training_record)
            new_examples += 1
        
        # Add to feedback log
        feedback_record = {
            **training_record,
            "discrepancy": f"AI said: '{ai_desc[:100]}...' vs Human said: '{human_desc[:100]}...'"
        }
        feedback_log.append(feedback_record)
    
    # 7. Save updated files
    save_json_file(training_file, training_data)
    save_json_file("learning/feedback_log.json", feedback_log)
    
    print("=" * 60)
    print(f"✅ FEEDBACK PROCESSED SUCCESSFULLY!")
    print(f"   📚 Added {new_examples} new training examples")
    print(f"   📁 Training file: {training_file}")
    print(f"   📊 Total training examples: {len(training_data)}")
    print("\n🔄 Next time you run descriptions.py with similar instructions,")
    print("   the AI will learn from these corrections!")
    print("=" * 60)


if __name__ == "__main__":
    process_feedback()
