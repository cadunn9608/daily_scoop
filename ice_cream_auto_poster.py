# --- 1. Load History to Prevent Repeats ---
history_file = "history.txt"
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

# --- 2. Dynamic Topic Generation with Built-In Validation Retry Loop ---
ai_trivia_raw = None
text_models_to_try = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

# We will try up to 3 generation attempts to ensure uniqueness
for attempt in range(3):
    trivia_prompt = (
        f"Attempt {attempt+1}: Generate a completely random, fascinating, and unique ice cream trivia fact (maximum 3 short sentences total). "
        "Choose an unexpected angle—focus on cultural oddities, historical figures, distribution methods, or manufacturing mechanics. "
        "Do not mention glowing items, jellyfish, marine biology, or rare orchids. "
        "Do not mention any commercial brand names."
        f"{history_exclusion} "
        "Output only the trivia content without any Markdown formatting or emojis."
    )

    candidate_text = None
    for model_name in text_models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=trivia_prompt)
            candidate_text = response.text.strip()
            if candidate_text:
                break
        except Exception:
            time.sleep(1)

    if candidate_text:
        # Simple keyword overlap check to catch accidental repeats
        candidate_lower = candidate_text.lower()
        is_too_similar = False
        for past in recent_history:
            past_words = set(w for w in past.lower().split() if len(w) > 4) # ignore small words
            candidate_words = set(w for w in candidate_lower.split() if len(w) > 4)
            common_words = past_words.intersection(candidate_words)
            # If 3 or more major descriptive words overlap, reject it as a duplicate topic
            if len(common_words) >= 3:
                is_too_similar = True
                print(f"Rejected candidate due to keyword overlap: {common_words}")
                break
        
        if not is_too_similar:
            ai_trivia_raw = candidate_text
            break
        else:
            time.sleep(2) # Wait a moment before retrying generation

if not ai_trivia_raw:
    raise Exception("All generation attempts failed to produce a unique trivia topic.")

# Clean up common prefixes
cleaned_trivia = ai_trivia_raw
prefixes_to_strip = [
    "ice cream trivia:", "did you know:", "trivia fact:", "fun fact:",
    "ice cream fact:", "ice cream fact", "trivia", "fact:"
]
lower_trivia = cleaned_trivia.lower()
for p in prefixes_to_strip:
    if lower_trivia.startswith(p):
        cleaned_trivia = cleaned_trivia[len(p):].strip()
        break

# Append the new unique trivia to history.txt immediately
with open(history_file, "a", encoding="utf-8") as f:
    f.write(cleaned_trivia + "\n")
print("Saved new unique trivia fact to history.txt")
