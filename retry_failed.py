"""
Retry failed URLs from the analysis.
Reads the output file, finds entries with errors, and re-processes them.
"""
import pandas as pd
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
import requests

from config import API_KEY, MODEL_NAME, RATE_LIMIT_DELAY
from scrapers.text_scraper import scrape_website_text
from scrapers.signal_extractor import extract_ui_signals
from ai.prompt_builder import build_prompt, load_training_examples, load_mistake_patterns
from descriptions import load_instructions, extract_benchmark_name

# Configure AI
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


def retry_failed(input_file: str):
    print("=" * 60)
    print("   RETRY FAILED URLs")
    print("=" * 60)
    
    # Load the output file
    df = pd.read_excel(input_file)
    
    # Find failed entries
    error_mask = df['AI_Description'] == "The Company's website does not work"
    failed_indices = df[error_mask].index.tolist()
    
    if not failed_indices:
        print("No failed URLs found!")
        return
    
    print(f"\nFound {len(failed_indices)} failed URLs to retry\n")
    
    # Load instructions
    instructions, visual_check = load_instructions()
    benchmark_name = extract_benchmark_name(instructions)
    training_examples = load_training_examples(benchmark_name)
    mistake_patterns = load_mistake_patterns()
    
    # Retry each failed URL
    fixed = 0
    for i, idx in enumerate(failed_indices):
        url = df.loc[idx, 'URL']
        print(f"[{i+1}/{len(failed_indices)}] Retrying: {url}")
        
        website_data = scrape_website_text(url)
        
        if not website_data.get('error'):
            # Success! Generate AI description
            ui_signals = {"has_shopping_cart": False, "has_job_board": False}
            
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
                df.loc[idx, 'AI_Description'] = response.text.strip()
                df.loc[idx, 'Html_Snippet'] = website_data.get('text_content', '')[:500]
                df.loc[idx, 'Nav_Links'] = ', '.join(website_data.get('nav_links', [])[:10])
                fixed += 1
                print(f"   ✓ Fixed!")
            except Exception as e:
                print(f"   ✗ AI Error: {e}")
        else:
            print(f"   ✗ Still failing: {website_data['error'][:50]}...")
        
        time.sleep(RATE_LIMIT_DELAY)
    
    # Save updated file
    df.to_excel(input_file, index=False)
    
    print("=" * 60)
    print(f"✅ Fixed {fixed}/{len(failed_indices)} URLs")
    print(f"   Remaining errors: {len(failed_indices) - fixed}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "zsalu_analysis.xlsx"
    retry_failed(input_file)
