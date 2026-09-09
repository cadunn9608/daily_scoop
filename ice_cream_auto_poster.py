import os
import time
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai

def make_bold(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return text.translate(str.maketrans(normal, bold))

def get_valid_facebook_token():
    """Automatically exchanges short-lived tokens for long-lived page tokens if App credentials are provided."""
    app_id = os.environ.get("FACEBOOK_APP_ID")
    app_secret = os.environ.get("FACEBOOK_APP_SECRET")
    initial_token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    page_id = os.environ.get("FACEBOOK_PAGE_ID")

    if not app_id or not app_secret:
        return initial_token

    try:
        exchange_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": initial_token
        }
        res = requests.get(exchange_url, params=params).json()
        long_lived_user_token = res.get("access_token")
        
        if not long_lived_user_token:
            return initial_token

        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"access_token": long_lived_user_token}
        pages_res = requests.get(pages_url, params=pages_params).json()

        for page in pages_res.get("data", []):
            if page.get("id") == page_id:
                return page.get("access_token")

        return long_lived_user_token
    except Exception:
        return initial_token

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

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

# --- 2. Dynamic Topic Generation with Broad Brand & Flavor Pillars ---
ai_trivia_raw = None
text_models_to_try = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

# Comprehensive domain stop words to ignore during similarity checks
domain_stopwords = {
    "cream", "answer", "history", "ice", "scoop", "scoops", "trivia", 
    "question", "fact", "during", "famous", "created", "invented", 
    "popular", "century", "people", "version", "first", "about", "their"
}

broad_brand_pillars = [
    "the surprising way a famous ice cream brand, parlor, or company got its start in the 19th or 20th century",
    "how a classic ice cream flavor, topping, or popular treat was accidentally or intentionally invented",
    "a fun historical milestone, cultural trend, or quirky milestone in the history of ice cream"
]

# Try up to 3 generation attempts to enforce absolute uniqueness
for attempt in range(3):
    selected_pillar = random.choice(broad_brand_pillars)
    trivia_prompt = (
        f"Attempt {attempt+1}: Generate a fascinating, storytelling-style trivia fact about ice cream focused on {selected_pillar} (between 3 to 5 sentences long). "
        "Write it like an engaging mini-story with a narrative arc, keeping it light, fun, and conversational. "
        "Do not mention glowing items, jellyfish, marine biology, or rare orchids. "
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
        # Keyword overlap check with clean punctuation stripping and expanded stopword filtering
        candidate_lower = candidate_text.lower()
        is_too_similar = False
        for past in recent_history:
            past_words = set(w.strip('.,!?:;"()') for w in past.lower().split() if len(w) > 4) - domain_stopwords
            candidate_words = set(w.strip('.,!?:;"()') for w in candidate_lower.split() if len(w) > 4) - domain_stopwords
            common_words = past_words.intersection(candidate_words)
            
            # Require at least 6 unique overlapping substantive words before flagging as a duplicate
            if len(common_words) >= 6:
                is_too_similar = True
                print(f"Rejected candidate due to keyword overlap: {common_words}")
                break
        
        if not is_too_similar:
            ai_trivia_raw = candidate_text
            break
        else:
            time.sleep(2)

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

header_tag = "★ DAILY ICE CREAM TRIVIA ★"
ai_trivia_formatted = make_bold(cleaned_trivia)

# --- 3. Randomized Cartoon Background Settings Pool ---
setting_choice = random.choice([
    "a high-tech futuristic ice cream testing laboratory with glowing holographic flavor charts and stainless steel tasting counters",
    "a cozy, sunlit wooden workshop filled with vintage ice cream churns, recipe notebooks, and colorful ingredient jars",
    "a whimsical modern kitchen workspace with digital flavor analysis screens and bubbling test tubes of sweet syrups",
    "a retro 1950s soda fountain counter with glittering chrome trim and glowing neon accent lights",
    "an interstellar spaceship kitchen equipped with zero-gravity refrigeration units and floating dessert spheres",
    "a magical candy-cane forest workshop with bubbling caramel cauldrons and sparkling sugar crystals",
    "a cozy Victorian parlor lit by candlelight with velvet armchairs, Persian rugs, and ancient leather-bound recipe books",
    "a high-altitude mountain observatory with snow-capped window views, brass telescopes, and antique barometers",
    "a bustling medieval alchemy tower filled with glowing potions, bubbling glass flasks, and ice-crystal instruments",
    "a tropical tiki-hut testing shack overlooking a sparkling blue lagoon with palm fronds and hanging fairy lights",
    "a steampunk clockwork laboratory with whirring brass gears, ticking gauges, and steam-powered stainless steel churns",
    "a cozy cabin kitchen during a gentle winter snowstorm with soft frost framing the windowpanes",
    "an underwater marine biology station with curved glass domes showing colorful coral reefs and swimming sea turtles",
    "a bustling carnival midway tent surrounded by colorful bunting, festive paper lanterns, and blue ribbon awards",
    "a sleek mid-century modern architectural studio with floor-to-ceiling glass windows and minimalist drafting tables",
    "a subterranean crystal cavern glowing softly with bioluminescent blue quartz crystals and mineral stalactites",
    "a retro drive-in diner kitchen with black-and-white checkered floors, stainless steel counters, and glowing jukeboxes",
    "a whimsical treehouse laboratory built inside a giant hollowed-out baobab tree with rope bridges and hanging ferns",
    "a futuristic lunar base observation dome overlooking the cratered grey moon surface and distant blue Earth",
    "a classic Parisian patisserie kitchen lightly dusted with powdered sugar, copper pans, and fresh vanilla pods",
    "a sun-drenched Mediterranean citrus orchard terrace with terracotta tiles, lemon trees, and striped canvas awnings",
    "a high-speed bullet train dining car zooming smoothly through a scenic alpine mountain landscape",
    "a cozy lighthouse keeper's room filled with nautical sea charts, brass instruments, and glowing storm lamps",
    "a mystical wizard's tower study stacked with ancient spellbooks, glowing runes, and floating measuring spoons",
    "a vintage 1920s jazz club backroom with deep velvet curtains, polished mahogany tables, and warm Edison bulbs",
    "a bustling artisan marketplace stall in a sunlit Italian piazza surrounded by cobblestones and flowering vines",
    "a high-tech environmental monitoring outpost nestled deep in an evergreen forest with wooden viewing decks",
    "a whimsical cloud-castle kitchen floating high above a soft blanket of white cumulus clouds with rainbow light",
    "a cozy country farmhouse kitchen featuring a heavy wood-burning stove and checkered tablecloths",
    "a futuristic underwater dome city laboratory with neon-lit aquatic plants and marine research monitors",
    "a magical toy workshop filled with mechanical wind-up gadgets, painted wooden shelves, and dollhouse displays",
    "a classic Hollywood movie studio prop room stacked with vintage cameras, director chairs, and theatrical spotlights",
    "a serene Japanese Zen garden tea house with smooth river rocks, raked gravel paths, and bonsai trees"
])

# --- 4. Randomized Scientist, Engineer, and Master Chef Roles & Actions ---
character_action_choice = random.choice([
    "wearing crisp white chef coats and tall toques while carefully measuring gourmet vanilla bean extract and tasting fresh cream samples",
    "wearing engineer goggles and hard hats while inspecting the complex plumbing and stainless-steel pressure valves of a custom ice cream churning machine",
    "wearing professional scientist lab coats and safety glasses while examining glowing chemical formulas and color-coded flavor charts on a futuristic digital display",
    "wearing professional chef aprons and holding wooden tasting spoons while testing the viscosity of rich chocolate fudge and caramel ribbons",
    "wearing engineer toolbelts and pocket protectors while tuning the precision temperature gauges of a cryogenic flash-freezing unit",
    "wearing white scientist lab coats and blue latex gloves while peering into microscopes to check fat crystal structures in a smooth dairy blend",
    "wearing classic master chef jackets and neckerchiefs while proudly rating the sweetness balance of various artisanal fruit purees",
    "wearing engineer headsets and high-tech utility belts while calibrating automated syrup dispensers on a stainless-steel production line",
    "wearing scientific safety goggles and lab coats while carefully mixing bubbling liquid nitrogen with sweet cream bases",
    "wearing classic master chef uniforms while meticulously decorating a beautifully crafted multi-tiered ice cream creation"
])

# --- 5. Locked Character Anchors (Matched precisely to the profile picture style) ---
andrew_character = "Andrew, a fluffy golden retriever puppy with warm golden fur, floppy ears, and friendly dark eyes, exactly matching the style in the profile picture"
petey_character = "Petey, an all-white puppy with clean white ears and a distinct black spot exclusively over his left eye, wearing a simple blue collar, exactly matching the style in the profile picture"

image_prompt = (
    f"A high-end 3D animated digital art piece in the distinct visual style of Pixar and Disney, "
    f"featuring {andrew_character} and {petey_character}, "
    f"working together inside {setting_choice}. "
    f"They are {character_action_choice}. "
    "Vibrant warm lighting, charming characters, polished cinematic digital rendering, perfect composition."
)

image_bytes = None
image_models_to_try = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image"
]

for img_model in image_models_to_try:
    try:
        response = client.models.generate_content(
            model=img_model,
            contents=image_prompt,
        )
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
            if image_bytes:
                break
        if image_bytes:
            break
    except Exception:
        time.sleep(2)

if not image_bytes:
    raise Exception("All Gemini image generation models failed to return image data.")

image_path = "temp_trivia_image.png"

# --- 6. Process Image & Render Pixel-Perfect Text Box Overlay ---
img = Image.open(BytesIO(image_bytes)).convert("RGBA")
img_width, img_height = img.size

try:
    font = ImageFont.truetype("DejaVuSans.ttf", 16)       # Balanced font size (16)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 21) # Balanced header font (21)
except IOError:
    font = ImageFont.load_default()
    header_font = font

box_x0 = 40
box_x1 = img_width - 40
max_text_width = (box_x1 - box_x0) - 50

wrapped_lines = []
for paragraph in cleaned_trivia.split("\n"):
    if not paragraph.strip():
        continue
    words = paragraph.strip().split()
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.getlength(test_line) <= max_text_width:
            current_line = test_line
        else:
            if current_line:
                wrapped_lines.append(current_line)
            current_line = word
    if current_line:
        wrapped_lines.append(current_line)

line_height = 22  # Balanced line spacing (22)
header_height = 30 
padding = 20
total_box_height = header_height + (len(wrapped_lines) * line_height) + (padding * 2)

box_y1 = img_height - 30
box_y0 = box_y1 - total_box_height

overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw_overlay = ImageDraw.Draw(overlay)

draw_overlay.rounded_rectangle(
    [box_x0, box_y0, box_x1, box_y1],
    radius=16,
    fill=(15, 23, 42, 235),
    outline=(245, 158, 11, 255),
    width=3
)

img = Image.alpha_composite(img, overlay).convert("RGB")
draw = ImageDraw.Draw(img)

text_x = box_x0 + 25
text_y = box_y0 + 16

draw.text((text_x, text_y), header_tag, fill=(252, 211, 77, 255), font=header_font)
text_y += header_height

for line in wrapped_lines:
    draw.text((text_x, text_y), line, fill=(241, 245, 249, 255), font=font)
    text_y += line_height

img.save(image_path, "PNG")

# --- 7. Format Social Media Caption Text ---
post_header = make_bold("🍦 THE DAILY SCOOP WITH PETEY & ANDREW 🐾\n\n")
engagement_cta = (
    "\n\n" + "🐕 " + make_bold("QUALITY CONTROL APPROVED!") + "\n" +
    "Andrew and Petey reviewed today's data from the lab and gave it two paws up. " +
    "What flavor are you tasting today? Let us know below! 👇"
)
post_text = post_header + ai_trivia_formatted + engagement_cta

# --- 8. Post the Branded Photo + Caption to Facebook Page Feed ---
page_id = os.environ["FACEBOOK_PAGE_ID"]
active_token = get_valid_facebook_token()
post_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"

with open(image_path, "rb") as img_file:
    files = {"source": img_file}
    payload = {
        "caption": post_text,
        "published": "true",
        "access_token": active_token
    }
    try:
        res = requests.post(post_url, data=payload, files=files)
        res_data = res.json()
        if "id" in res_data:
            print(f"Successfully posted to Facebook! Post ID: {res_data['id']}")
        else:
            print(f"Failed to post to Facebook: {res_data}")
    except Exception as e:
        print(f"Exception occurred while posting to Facebook: {e}")
