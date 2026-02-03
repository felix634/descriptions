"""
Signal Extractor Module
Extracts additional signals from website HTML beyond text content.
Includes UI element detection (shopping cart, etc.) when requested.
"""
from bs4 import BeautifulSoup
import requests
from config import REQUEST_TIMEOUT


def extract_ui_signals(soup: BeautifulSoup, visual_check: str = "") -> dict:
    """
    Extracts UI signals based on optional visual check instructions.
    
    Args:
        soup: BeautifulSoup object of the page
        visual_check: Optional instruction for what to look for (e.g., "shopping cart icon")
    
    Returns:
        dict: {
            "has_shopping_cart": bool,
            "has_job_board": bool,
            "detected_elements": list[str],
            "custom_check_result": str
        }
    """
    result = {
        "has_shopping_cart": False,
        "has_job_board": False,
        "detected_elements": [],
        "custom_check_result": ""
    }
    
    # Common shopping cart indicators
    cart_patterns = [
        'cart', 'basket', 'shopping-cart', 'shopping_cart', 
        'add-to-cart', 'addtocart', 'buy-now', 'checkout',
        'shop', 'store', 'e-commerce', 'ecommerce'
    ]
    
    # Check for shopping cart elements
    for pattern in cart_patterns:
        # Check class names
        elements = soup.find_all(class_=lambda x: x and pattern in x.lower() if x else False)
        if elements:
            result["has_shopping_cart"] = True
            result["detected_elements"].append(f"cart-indicator: {pattern}")
            break
        
        # Check IDs
        elements = soup.find_all(id=lambda x: x and pattern in x.lower() if x else False)
        if elements:
            result["has_shopping_cart"] = True
            result["detected_elements"].append(f"cart-id: {pattern}")
            break
        
        # Check for cart icons (common icon libraries)
        icons = soup.find_all(['i', 'span', 'svg'], class_=lambda x: x and pattern in x.lower() if x else False)
        if icons:
            result["has_shopping_cart"] = True
            result["detected_elements"].append(f"cart-icon: {pattern}")
            break
    
    # Check for job board / careers section
    job_patterns = ['careers', 'jobs', 'vacancies', 'hiring', 'join-us', 'join-our-team']
    for pattern in job_patterns:
        links = soup.find_all('a', href=lambda x: x and pattern in x.lower() if x else False)
        if links:
            result["has_job_board"] = True
            result["detected_elements"].append(f"job-board: {pattern}")
            break
        
        text_elements = soup.find_all(string=lambda x: x and pattern.replace('-', ' ') in x.lower() if x else False)
        if text_elements:
            result["has_job_board"] = True
            result["detected_elements"].append(f"job-mention: {pattern}")
            break
    
    # Process custom visual check if provided
    if visual_check.strip():
        result["custom_check_result"] = process_custom_visual_check(soup, visual_check)
    
    return result


def process_custom_visual_check(soup: BeautifulSoup, instruction: str) -> str:
    """
    Processes custom visual check instructions.
    Returns a description of what was found.
    """
    instruction_lower = instruction.lower()
    findings = []
    
    # Common check patterns
    if 'shopping cart' in instruction_lower or 'cart icon' in instruction_lower:
        cart_elements = soup.find_all(class_=lambda x: x and 'cart' in x.lower() if x else False)
        if cart_elements:
            findings.append("Shopping cart element detected")
        else:
            findings.append("No shopping cart element found")
    
    if 'contact form' in instruction_lower:
        forms = soup.find_all('form')
        contact_forms = [f for f in forms if 'contact' in str(f).lower() or 'message' in str(f).lower()]
        if contact_forms:
            findings.append("Contact form detected")
        else:
            findings.append("No contact form found")
    
    if 'product' in instruction_lower and 'page' in instruction_lower:
        product_indicators = soup.find_all(class_=lambda x: x and 'product' in x.lower() if x else False)
        if product_indicators:
            findings.append("Product pages detected")
        else:
            findings.append("No product page indicators found")
    
    return "; ".join(findings) if findings else "Custom check performed, no specific findings"
