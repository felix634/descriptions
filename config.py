# Configuration for Company Benchmarking Tool
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# API Configuration
API_KEY = os.getenv("GEMINI_API_KEY", "")

# File paths
INPUT_FILE = "company_list.xlsx"
OUTPUT_FILE = "completed_analysis.xlsx"

# AI Model Configuration
MODEL_NAME = "gemini-2.0-flash"

# Scraping Configuration
REQUEST_TIMEOUT = 15
TEXT_LIMIT = 6000  # Max characters to send to AI
RATE_LIMIT_DELAY = 5  # Seconds between API calls

# Confidence Thresholds
AUTO_ACCEPT_THRESHOLD = 0.90
NEEDS_VERIFICATION_THRESHOLD = 0.70
