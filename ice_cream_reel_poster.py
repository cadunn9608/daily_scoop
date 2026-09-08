# --- 1. Load Reel History and Run Validation Retry Loop ---
history_file = "reel_history.txt"
past_trivia = []
if os.path.exists(history_file):
    with open(history_file, "r", encoding="utf-8") as f:
        past_trivia = [line.strip() for line in f if line.strip()]

recent_history = past_trivia[-80:] if past_trivia else []
history_exclusion = ""
if recent_history:
    history_exclusion = (
        " STRICT BLACKLIST — DO NOT mention, reference, or write about any of these past subjects, ingredients, or themes: "
        + " | ".join(recent_history)
        + ". Your topic must be fundamentally different in category, country, and science."
    )

ai_trivia_raw = None
text_models_to_try = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest"
]

# Comprehensive domain stop words to ignore during similarity checks
domain_stopwords = {
    "cream", "answer", "history", "ice", "scoop", "scoops", "trivia", 
    "question", "fact", "during", "famous", "created", "invented", 
    "popular", "century", "people", "version", "first", "about", "their"
}

for attempt in range(3):
    trivia_prompt = (
        f"Attempt {attempt+1}: Act as an expert trivia host and culinary historian. "
        "Generate 1 captivating, unique ice cream trivia fact from the year 1900 through the early 1900s. "
        "Format your response into 3 distinct lines using safe text symbols (like ★ or ►) instead of emojis: "
        "Line 1: A catchy hook/intro with a symbol (e.g., [★] COOL COLD HISTORY!). "
        "Line 2: The trivia question or setup (e.g., What iconic 1920 sweet treat was born from a boy's indecision?). "
        "Line 3: The exciting answer and brief explanation with a symbol (e.g., [►] ANSWER: The Eskimo Pie, invented by an Iowa teacher!). "
        "Keep the total word count under 50 words so it fits comfortably in a mobile video overlay box. "
        f"{history_exclusion} "
        "Output only the 3 text lines without Markdown bolding asterisks."
    )

    candidate_text = None
    for model_name in text_models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=trivia_prompt)
            candidate_text = response.text.strip()
            if candidate_text:
                print(f"Successfully generated reel trivia using model: {model_name}")
                break
        except Exception:
            time.sleep(1)

    if candidate_text:
        candidate_lower = candidate_text.lower()
        is_too_similar = False
        for past in recent_history:
            # Strip all punctuation cleanly and remove domain stopwords
            past_words = set(w.strip('.,!?:;"()') for w in past.lower().split() if len(w) > 4) - domain_stopwords
            candidate_words = set(w.strip('.,!?:;"()') for w in candidate_lower.split() if len(w) > 4) - domain_stopwords
            common_words = past_words.intersection(candidate_words)
            
            # Require at least 6 unique overlapping substantive words before flagging as a duplicate
            if len(common_words) >= 6:
                is_too_similar = True
                print(f"Rejected Reel candidate due to keyword overlap: {common_words}")
                break
        
        if not is_too_similar:
            ai_trivia_raw = candidate_text
            break
        else:
            time.sleep(2)

if not ai_trivia_raw:
    raise Exception("All text models failed to generate unique reel trivia content.")

cleaned_trivia = ai_trivia_raw

with open(history_file, "a", encoding="utf-8") as f:
    f.write(cleaned_trivia.replace("\n", " ") + "\n")
print("Saved new unique reel trivia fact to reel_history.txt")
