import pandas as pd

import requests

from bs4 import BeautifulSoup

import json

import time

import google.generativeai as genai

import os



# --- CONFIGURATION ---

# 1. Get your API Key from https://aistudio.google.com/

API_KEY = "AIzaSyC7YLzhhP2dRju6lAx75m5HAZ_tEW_vheE"



# 2. File Configuration

INPUT_FILE = "company_list.xlsx"        # The Excel file with URLs

OUTPUT_FILE = "completed_analysis.xlsx" # The Excel file the code creates

TRAINING_FILE = "training_examples.json" # The "Brain" (Style examples)

INSTRUCTION_FILE = "task_instructions.txt" # The "Mission" (Specific task/Question)



# 3. Configure AI

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash')



def load_file_content(filepath, is_json=False):

    """

    Reads the content of the external instruction files.

    """

    if not os.path.exists(filepath):

        print(f"Warning: File not found: {filepath}")

        return None if is_json else ""

   

    try:

        with open(filepath, 'r', encoding='utf-8') as f:

            if is_json:

                return json.load(f)

            return f.read().strip()

    except Exception as e:

        print(f"Error reading {filepath}: {e}")

        return None if is_json else ""



def scrape_website_text(url):

    """

    Visits the website and extracts the visible text.

    """

    if pd.isna(url) or url == "":

        return "No URL provided"

       

    if not url.startswith(('http://', 'https://')):

        url = 'https://' + url

       

    headers = {

        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    }

   

    try:

        print(f"   Scraping: {url}...")

        response = requests.get(url, headers=headers, timeout=15)

        response.raise_for_status()

       

        soup = BeautifulSoup(response.text, 'html.parser')

       

        # Clean up: remove code, scripts, and styling

        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):

            element.extract()

           

        # Extract text

        text = soup.get_text(separator=' ')

       

        # Clean up white space

        lines = (line.strip() for line in text.splitlines())

        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

        clean_text = ' '.join(chunk for chunk in chunks if chunk)

       

        # Return the first 6000 characters to keep AI costs low and speed high

        return clean_text[:6000]

       

    except Exception as e:

        return f"Scraping Error: {e}"



def generate_ai_description(website_text, global_instructions, examples):

    """

    The Core AI Function.

    It combines:

    1. The Mission (from your txt file)

    2. The Style (from your json file)

    3. The Website Content (from the scraper)

    """

    if "Error" in website_text or website_text == "No URL provided":

        return website_text



    # Prepare the "Training/Style" section of the prompt

    formatted_examples = ""

    if examples:

        formatted_examples = "REFERENCE EXAMPLES (Use this writing style):\n"

        for ex in examples:

            formatted_examples += f"""

            --- Example Start ---

            Web Snippet: "{ex.get('content_snippet', '')[:100]}..."

            Ideal Output: {ex.get('description', '')}

            --- Example End ---

            """



    # Construct the final prompt sent to Google Gemini

    prompt = f"""

    ROLE:

    You are an expert business analyst.

   

    THE MISSION (Instructions from the user):

    {global_instructions}



    {formatted_examples}



    --------------------------------------------------

   

    CURRENT TASK:

    Analyze the website text below and strictly follow 'The Mission'.

   

    WEBSITE CONTENT:

    {website_text}

   

    OUTPUT:

    """



    try:

        response = model.generate_content(prompt)

        return response.text.strip()

    except Exception as e:

        return f"AI Generation Error: {e}"



def main():

    print("--- AI Company Analyst Tool ---")

   

    # 1. Load the specific instruction text file

    mission_text = load_file_content(INSTRUCTION_FILE)

    if not mission_text:

        print(f"CRITICAL ERROR: Could not find {INSTRUCTION_FILE}. Please create this file with your instructions.")

        return

    print(f"Loaded Mission Instructions: \n'{mission_text[:100]}...'")



    # 2. Load the training examples

    training_data = load_file_content(TRAINING_FILE, is_json=True)

    if not training_data:

        print("Notice: No training examples found. Running without style examples.")

        training_data = []

    else:

        print(f"Loaded {len(training_data)} training examples.")



    # 3. Load the Excel file

    try:

        df = pd.read_excel(INPUT_FILE)

        if 'URL' not in df.columns:

            print("Error: Excel file must have a column named 'URL'")

            return

    except Exception as e:

        print(f"Error opening Excel file: {e}")

        return



    # 4. Loop through the Excel rows

    results = []

    print(f"Starting analysis of {len(df)} companies...")

   

    for index, row in df.iterrows():

        url = row['URL']

       

        # Step A: Get the text

        web_content = scrape_website_text(url)

       

        # Step B: Analyze it using the instructions + examples

        if "Error" not in web_content:

            analysis = generate_ai_description(web_content, mission_text, training_data)

        else:

            analysis = web_content # Just save the error message if scraping failed

           

        results.append(analysis)

       

        # Sleep briefly to avoid hitting API limits

        time.sleep(5)



    # 5. Save the results to a new Excel file

    df['AI Analysis'] = results

    df.to_excel(OUTPUT_FILE, index=False)

    print(f"\nSuccess! Analysis saved to {OUTPUT_FILE}")



if __name__ == "__main__":

    main()