import os
import time
import random
import subprocess
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai

def make_bold(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙G𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
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
        
        if "error" in res:
            print(f"Warning: Token exchange failed: {res['error'].get('message')}")
            return initial_token
            
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
    except Exception as e:
        print(f"Warning: Exception during token refresh: {e}")
        return initial_token

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

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

domain_stopwords = {
    "cream", "answer", "history", "ice", "scoop", "scoops", "trivia", 
    "question", "fact", "during", "famous", "created", "invented", 
    "popular", "century", "people", "version", "first", "about", "their"
}

for attempt in range(3):
    trivia_prompt = (
        f"Attempt {attempt+1}: Act as an expert trivia host and culinary historian. "
        "Generate 1 captivating, unique ice cream trivia fact from history. "
        "Format your response into 3 distinct lines using safe text symbols (like ★ or ►) instead of emojis: "
        "Line 1: A catchy hook/intro with a symbol (e.g., [★] COOL COLD HISTORY!). "
        "Line 2: The trivia question or setup (e.g., What iconic sweet treat was born from a boy's indecision?). "
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
            past_words = set(w.strip('.,!?:;"()') for w in past.lower().split() if len(w) > 4) - domain_stopwords
            candidate_words = set(w.strip('.,!?:;"()') for w in candidate_lower.split() if len(w) > 4) - domain_stopwords
            common_words = past_words.intersection(candidate_words)
            
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

header_tag = "★ DAILY ICE CREAM REEL ★"
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
    "a vibrant carnival midway tent surrounded by colorful bunting, festive paper lanterns, and blue ribbon awards",
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

# --- 5. Locked Character Anchors ---
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

image_path = "temp_reel_image.png"

# --- 6. Process Image & Render Text Box Overlay (Positioned at the TOP) ---
img = Image.open(BytesIO(image_bytes)).convert("RGBA")
img_width, img_height = img.size

try:
    font = ImageFont.truetype("DejaVuSans.ttf", 18)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
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

line_height = 24
header_height = 32
padding = 20
total_box_height = header_height + (len(wrapped_lines) * line_height) + (padding * 2)

# Position text box at the TOP of the image so it doesn't block characters/table
box_y0 = 40
box_y1 = box_y0 + total_box_height

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

# --- 7. Convert Image to MP4 Video with FFmpeg for Reels ---
video_path = "temp_reel_video.mp4"
print("Converting image to 6-second MP4 video with FFmpeg...")

ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-i", image_path,
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-c:v", "libx264",
    "-t", "6",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    video_path
]

subprocess.run(ffmpeg_cmd, check=True)
print("Video reel file created successfully.")

# --- 8. Format Social Media Caption Text ---
post_header = make_bold("🍦 THE DAILY ICE CREAM REEL WITH PETEY & ANDREW 🐾\n\n")
engagement_cta = (
    "\n\n" + "🐕 " + make_bold("LAB TESTED & APPROVED!") + "\n" +
    "Andrew and Petey checked the data logs on this one. What's your top flavor? Drop it below! 👇"
)
post_text = post_header + ai_trivia_formatted + engagement_cta

# --- 9. Post Video to Facebook Reels Endpoint ---
page_id = os.environ["FACEBOOK_PAGE_ID"]
active_token = get_valid_facebook_token()
post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"

with open(video_path, "rb") as vid_file:
    files = {"source": vid_file}
    payload = {
        "description": post_text,
        "media_type": "REELS",
        "access_token": active_token
    }
    try:
        res = requests.post(post_url, data=payload, files=files)
        res_data = res.json()
        if "id" in res_data:
            print(f"Successfully posted Reel video to Facebook! Post ID: {res_data['id']}")
        else:
            print(f"Failed to post Reel to Facebook: {res_data}")
    except Exception as e:
        print(f"Exception occurred while posting Reel to Facebook: {e}")
