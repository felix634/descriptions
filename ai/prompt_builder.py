"""
Prompt Builder Module
Constructs AI prompts dynamically based on:
- User instructions (on-the-fly benchmark definition)
- Training examples (benchmark-specific if available)
- Mistake patterns (global corrections)
- Website signals (text, nav links, UI elements)
"""
import json
import os


def build_prompt(
    website_data: dict,
    instructions: str,
    visual_check: str,
    training_examples: list,
    mistake_patterns: list,
    ui_signals: dict = None
) -> str:
    """
    Builds the complete prompt for the AI model.
    
    Args:
        website_data: Dict with text_content, nav_links, meta_description
        instructions: User's benchmark instructions
        visual_check: Optional visual check instruction
        training_examples: List of example dicts
        mistake_patterns: List of common mistake patterns to avoid
        ui_signals: Dict with detected UI elements
    
    Returns:
        str: Complete prompt for the AI
    """
    
    # Build the training examples section
    examples_section = ""
    if training_examples:
        examples_section = "REFERENCE EXAMPLES (Match this writing style and analysis depth):\n"
        for i, ex in enumerate(training_examples, 1):
            examples_section += f"""
--- Example {i} ---
Instructions Used: {ex.get('benchmark_context', 'N/A')}
Website Snippet: "{ex.get('html_snippet', ex.get('content_snippet', ''))[:150]}..."
Correct Output: {ex.get('human_description', ex.get('description', ''))}
--- End Example {i} ---
"""
    
    # Build the mistake avoidance section
    mistakes_section = ""
    if mistake_patterns:
        mistakes_section = "\n⚠️ COMMON MISTAKES TO AVOID:\n"
        for pattern in mistake_patterns:
            mistakes_section += f"""
- Pattern: "{pattern.get('pattern', '')}"
  WRONG conclusion: {pattern.get('wrong_conclusion', '')}
  CORRECT conclusion: {pattern.get('correct_conclusion', '')}
"""
    
    # Build the signals section
    signals_section = build_signals_section(website_data, ui_signals)
    
    # Build the visual check section if provided
    visual_section = ""
    if visual_check.strip():
        visual_section = f"\nVISUAL CHECK REQUESTED:\n{visual_check}\n"
        if ui_signals and ui_signals.get('custom_check_result'):
            visual_section += f"Detection Result: {ui_signals['custom_check_result']}\n"
    
    # Construct final prompt
    prompt = f"""ROLE:
You are an expert business analyst specializing in company benchmarking studies.

THE MISSION (Instructions for this benchmark):
{instructions}
{visual_section}
{examples_section}
{mistakes_section}
--------------------------------------------------

CURRENT TASK:
Analyze the website content below and strictly follow 'The Mission'.

{signals_section}

WEBSITE TEXT CONTENT:
{website_data.get('text_content', '')}

OUTPUT:
Provide your analysis following the mission instructions exactly.
"""
    
    return prompt


def build_signals_section(website_data: dict, ui_signals: dict = None) -> str:
    """Builds the signals section of the prompt."""
    sections = []
    
    # Navigation links
    nav_links = website_data.get('nav_links', [])
    if nav_links:
        # Filter to most relevant links
        relevant_keywords = ['r&d', 'research', 'product', 'service', 'about', 
                           'shop', 'store', 'career', 'contact', 'solution',
                           'manufacture', 'develop', 'wholesale', 'retail']
        filtered_links = [link for link in nav_links[:30] 
                         if any(kw in link.lower() for kw in relevant_keywords)]
        if filtered_links:
            sections.append(f"NAVIGATION LINKS DETECTED: {', '.join(filtered_links[:15])}")
    
    # Meta description
    meta = website_data.get('meta_description', '')
    if meta:
        sections.append(f"META DESCRIPTION: {meta}")
    
    # UI signals
    if ui_signals:
        if ui_signals.get('has_shopping_cart'):
            sections.append("⚡ RETAIL INDICATOR: Shopping cart/e-commerce elements detected")
        if ui_signals.get('has_job_board'):
            sections.append("📋 CAREERS SECTION: Job board/hiring page detected")
        if ui_signals.get('detected_elements'):
            sections.append(f"UI ELEMENTS: {', '.join(ui_signals['detected_elements'][:5])}")
    
    return "\n".join(sections) if sections else ""


def load_training_examples(benchmark_name: str, learning_dir: str = "learning") -> list:
    """
    Loads training examples for a specific benchmark type.
    Falls back to generic examples if benchmark-specific not found.
    """
    examples = []
    
    # Try benchmark-specific file first
    specific_file = os.path.join(learning_dir, f"training_{benchmark_name.lower().replace(' ', '_')}.json")
    if os.path.exists(specific_file):
        try:
            with open(specific_file, 'r', encoding='utf-8') as f:
                examples = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load {specific_file}: {e}")
    
    # Also load from the original training file if exists
    generic_file = "training_examples.json"
    if os.path.exists(generic_file):
        try:
            with open(generic_file, 'r', encoding='utf-8') as f:
                generic_examples = json.load(f)
                examples.extend(generic_examples)
        except Exception as e:
            print(f"Warning: Could not load {generic_file}: {e}")
    
    return examples


def load_mistake_patterns(learning_dir: str = "learning") -> list:
    """Loads global mistake patterns."""
    patterns_file = os.path.join(learning_dir, "mistake_patterns.json")
    
    if os.path.exists(patterns_file):
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both formats: {"common_mistakes": [...]} or [...]
                if isinstance(data, dict):
                    return data.get('common_mistakes', [])
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"Warning: Could not load mistake patterns: {e}")
    
    return []
