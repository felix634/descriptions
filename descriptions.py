"""
Adaptive Company Benchmarking Tool
Version 2.0 - With feedback learning and dynamic benchmark support

This tool:
1. Scrapes company websites
2. Extracts text + navigation signals + UI elements
3. Uses AI to generate descriptions based on your on-the-fly benchmark instructions
4. Outputs to Excel with columns for your corrections
5. Learns from your feedback over time
"""
import pandas as pd
import json
import time
import os
import re
import sys
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests

# Import from modular structure
from config import (
    API_KEY, INPUT_FILE, OUTPUT_FILE, MODEL_NAME,
    TEXT_LIMIT, RATE_LIMIT_DELAY
)
from scrapers.text_scraper import scrape_website_text
from scrapers.signal_extractor import extract_ui_signals
from ai.prompt_builder import (
    build_prompt, load_training_examples, load_mistake_patterns
)


# Configure AI
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
else:
    print("WARNING: No API key found. Set GEMINI_API_KEY environment variable.")
    model = None


def load_instructions(filepath: str = "task_instructions.txt") -> tuple:
    """
    Loads instructions and extracts VISUAL_CHECK if present.
    
    Returns:
        tuple: (main_instructions, visual_check)
    """
    if not os.path.exists(filepath):
        return "", ""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract VISUAL_CHECK line if present
        visual_check = ""
        visual_match = re.search(r'VISUAL_CHECK:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        if visual_match:
            visual_check = visual_match.group(1).strip()
            # Remove the VISUAL_CHECK line from main instructions
            content = re.sub(r'VISUAL_CHECK:\s*.+?(?:\n|$)', '', content, flags=re.IGNORECASE)
        
        return content.strip(), visual_check
    
    except Exception as e:
        print(f"Error reading instructions: {e}")
        return "", ""


def extract_benchmark_name(instructions: str) -> str:
    """
    Extracts a benchmark name from instructions for training file naming.
    Uses first few significant words.
    """
    # Remove common words and extract key terms
    words = instructions.lower().split()[:20]
    stop_words = {'we', 'are', 'the', 'a', 'an', 'for', 'of', 'to', 'in', 'on', 'is', 
                  'please', 'write', 'analyzing', 'looking', 'describe', 'description'}
    key_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Take first 3 meaningful words
    benchmark_name = '_'.join(key_words[:3]) if key_words else 'general'
    return benchmark_name


def generate_ai_description(website_data: dict, ui_signals: dict, 
                            instructions: str, visual_check: str,
                            training_examples: list, mistake_patterns: list) -> str:
    """
    Generates AI description using all available signals.
    """
    if not model:
        return "The Company's website does not work"
    
    if website_data.get('error'):
        return "The Company's website does not work"
    
    # Build the prompt
    prompt = build_prompt(
        website_data=website_data,
        instructions=instructions,
        visual_check=visual_check,
        training_examples=training_examples,
        mistake_patterns=mistake_patterns,
        ui_signals=ui_signals
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI Generation Error: {e}"


def main():
    print("=" * 60)
    print("   ADAPTIVE COMPANY BENCHMARKING TOOL v2.0")
    print("=" * 60)
    
    # Handle command line arguments
    input_file = INPUT_FILE
    output_file = OUTPUT_FILE
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        # Auto-generate output name from input
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_analysis.xlsx"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # 1. Load instructions (with optional visual check)
    instructions, visual_check = load_instructions()
    if not instructions:
        print("❌ CRITICAL: No instructions found. Create task_instructions.txt")
        return
    
    print(f"\n📋 Loaded Instructions:\n   '{instructions[:80]}...'")
    if visual_check:
        print(f"👁️  Visual Check: {visual_check}")
    
    # 2. Determine benchmark name for training file lookup
    benchmark_name = extract_benchmark_name(instructions)
    print(f"🏷️  Benchmark Type: {benchmark_name}")
    
    # 3. Load training examples and mistake patterns
    training_examples = load_training_examples(benchmark_name)
    mistake_patterns = load_mistake_patterns()
    print(f"📚 Loaded {len(training_examples)} training examples")
    print(f"⚠️  Loaded {len(mistake_patterns)} mistake patterns")
    
    # 4. Load input Excel file
    try:
        df = pd.read_excel(input_file)
        if 'URL' not in df.columns:
            print("❌ Error: Excel must have a 'URL' column")
            return
    except Exception as e:
        print(f"❌ Error loading Excel: {e}")
        return
    
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_file}")
    print(f"\n🔍 Starting analysis of {len(df)} companies...\n")
    
    # 5. Prepare output columns
    results = []
    html_snippets = []  # Store for feedback loop
    nav_links_col = []
    ui_signals_col = []
    
    # 6. Process each company
    for index, row in df.iterrows():
        url = row['URL']
        print(f"[{index + 1}/{len(df)}] Processing: {url}")
        
        # Scrape website
        website_data = scrape_website_text(url)
        
        # Extract UI signals if needed
        ui_signals = {"has_shopping_cart": False, "has_job_board": False}
        if visual_check and not website_data.get('error'):
            # Re-fetch for UI analysis (we need the raw HTML)
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
                resp = requests.get(url if url.startswith('http') else f'https://{url}', 
                                    headers=headers, timeout=15)
                soup = BeautifulSoup(resp.text, 'html.parser')
                ui_signals = extract_ui_signals(soup, visual_check)
            except:
                pass
        
        # Generate AI description
        if not website_data.get('error'):
            analysis = generate_ai_description(
                website_data, ui_signals, instructions, visual_check,
                training_examples, mistake_patterns
            )
        else:
            analysis = website_data['error']
        
        # Collect results
        results.append(analysis)
        html_snippets.append(website_data.get('text_content', '')[:500])
        nav_links_col.append(', '.join(website_data.get('nav_links', [])[:10]))
        ui_signals_col.append(str(ui_signals.get('detected_elements', [])))
        
        print(f"   ✓ Done\n")
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    # 7. Save to Excel with feedback columns
    df['AI_Description'] = results
    df['Your_Correction'] = ''  # Empty column for your corrections
    df['Html_Snippet'] = html_snippets
    df['Nav_Links'] = nav_links_col
    df['UI_Signals'] = ui_signals_col
    
    df.to_excel(output_file, index=False)
    
    print("=" * 60)
    print(f"✅ SUCCESS! Results saved to: {output_file}")
    print("\n📝 NEXT STEPS FOR FEEDBACK LOOP:")
    print("   1. Open the Excel file")
    print("   2. Review 'AI_Description' column")
    print("   3. Add your corrections in 'Your_Correction' column")
    print("   4. Run: python feedback_processor.py")
    print("=" * 60)


if __name__ == "__main__":
    main()