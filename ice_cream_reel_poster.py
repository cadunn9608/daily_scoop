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
        "Format your response with explicit line breaks: "
        "Line 1: A catchy hook/intro with a symbol (e.g., [★] COOL COLD HISTORY!). "
        "Line 2: The trivia question or setup (e.g., What iconic sweet treat was born from a boy's indecision?). "
        "[Leave a blank line here] "
        "Line 3: The exciting answer and brief explanation with a symbol (e.g., [►] ANSWER: The Eskimo Pie, invented by an Iowa teacher!). "
        "Keep the total word count under 40 words so it fits comfortably in a mobile video overlay box with large font. "
        f"{history_exclusion} "
        "Output only the text lines without Markdown bolding asterisks."
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

ai_trivia_formatted = make_bold(cleaned_trivia)

# --- 3. Randomized Cartoon Background Settings Pool ---
setting_choice = random.choice([
    "a high-tech futuristic ice cream testing laboratory with glowing holographic flavor charts",
    "a retro 1950s soda fountain counter with glittering chrome trim and glowing neon accent lights",
    "a steampunk clockwork laboratory with whirring brass gears, ticking gauges, and steam-powered stainless steel churns",
    "a classic Parisian patisserie kitchen lightly dusted with powdered sugar, copper pans, and fresh vanilla pods",
    "a cozy, sunlit wooden workshop filled with vintage ice cream churns, recipe notebooks, and colorful ingredient jars",
    "a magical candy-cane forest workshop with bubbling caramel cauldrons and sparkling sugar crystals",
    "an underwater marine biology station with curved glass domes showing colorful coral reefs and swimming sea turtles"
])

# --- 4. Randomized Scientist, Engineer, and Master Chef Roles & Actions ---
character_action_choice = random.choice([
    "wearing crisp white chef coats and tall toques while carefully measuring gourmet vanilla bean extract",
    "wearing engineer goggles and hard hats while inspecting the complex plumbing of a custom ice cream churning machine",
    "wearing professional scientist lab coats and safety glasses while examining glowing chemical formulas",
    "wearing professional chef aprons and holding wooden tasting spoons while testing the viscosity of rich chocolate fudge"
])

# --- 5. Locked Character Anchors ---
andrew_character = "Andrew, a fluffy golden retriever puppy with warm golden fur, floppy ears, and friendly dark eyes"
petey_character = "Petey, an all-white puppy with clean white ears and a distinct black spot exclusively over his left eye, wearing a simple blue collar"

image_prompt = (
    f"A vertical portrait orientation (9:16 aspect ratio) high-end 3D animated digital art piece in the distinct visual style of Pixar and Disney, "
    f"featuring {andrew_character} and {petey_character}, "
    f"working together inside {setting_choice}. "
    f"They are {character_action_choice}. "
    "Vibrant warm lighting, charming characters, polished cinematic digital rendering, perfect composition."
)

image_bytes = None
image_models_to_try = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-3-pro-image"]

for img_model in image_models_to_try:
    try:
        response = client.models.generate_content(model=img_model, contents=image_prompt)
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
            if image_bytes: break
        if image_bytes: break
    except Exception:
        time.sleep(2)

if not image_bytes:
    raise Exception("All Gemini image generation models failed to return image data.")

image_path = "temp_reel_image.png"

# --- 6. Image Resizing (9:16 Ratio) & Render Text Box with Explicit Line Break ---
img = Image.open(BytesIO(image_bytes)).convert("RGBA")

target_width = 1080
target_height = 1920
img_ratio = img.width / img.height
target_ratio = target_width / target_height

if img_ratio > target_ratio:
    new_height = target_height
    new_width = int(new_height * img_ratio)
else:
    new_width = target_width
    new_height = int(new_width / img_ratio)

img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
left = (new_width - target_width) / 2
top = (new_height - target_height) / 2
right = (new_width + target_width) / 2
bottom = (new_height + target_height) / 2
img = img.crop((left, top, right, bottom))

img_width, img_height = img.size

try:
    font = ImageFont.truetype("DejaVuSans.ttf", 36)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
except IOError:
    font = ImageFont.load_default()
    header_font = font

# Separate sections cleanly
trivia_lines = [p.strip() for p in cleaned_trivia.split("\n") if p.strip()]
header_text = trivia_lines[0] if len(trivia_lines) > 0 else "[★] ICE CREAM HISTORY"
question_text = trivia_lines[1] if len(trivia_lines) > 1 else ""
answer_text = " ".join(trivia_lines[2:]) if len(trivia_lines) > 2 else ""

box_x0 = 50
box_x1 = img_width - 50
max_text_width = (box_x1 - box_x0) - 60

def wrap_text(text, font_obj, max_w):
    lines = []
    current_line = ""
    for word in text.split():
        test_line = f"{current_line} {word}".strip()
        if font_obj.getlength(test_line) <= max_w:
            current_line = test_line
        else:
            if current_line: lines.append(current_line)
            current_line = word
    if current_line: lines.append(current_line)
    return lines

wrapped_header = wrap_text(header_text, header_font, max_text_width)
wrapped_question = wrap_text(question_text, font, max_text_width)
wrapped_answer = wrap_text(answer_text, font, max_text_width)

header_line_height = 52
body_line_height = 46
padding = 35
section_gap = 25  # Explicit visual line break spacing between question and answer

total_box_height = (
    (len(wrapped_header) * header_line_height) + 
    (len(wrapped_question) * body_line_height) + 
    (len(wrapped_answer) * body_line_height) + 
    section_gap + 
    (padding * 2) + 15
)

box_y0 = 120
box_y1 = box_y0 + total_box_height

overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw_overlay = ImageDraw.Draw(overlay)

draw_overlay.rounded_rectangle(
    [box_x0, box_y0, box_x1, box_y1],
    radius=24,
    fill=(15, 23, 42, 235),
    outline=(245, 158, 11, 255),
    width=4
)

img = Image.alpha_composite(img, overlay).convert("RGB")
draw = ImageDraw.Draw(img)

text_x = box_x0 + 30
text_y = box_y0 + padding

# Draw Header
for line in wrapped_header:
    draw.text((text_x, text_y), line, fill=(252, 211, 77, 255), font=header_font)
    text_y += header_line_height

text_y += 10

# Draw Question
for line in wrapped_question:
    draw.text((text_x, text_y), line, fill=(241, 245, 249, 255), font=font)
    text_y += body_line_height

# Insert explicit line break gap before the answer block
text_y += section_gap

# Draw Answer
for line in wrapped_answer:
    draw.text((text_x, text_y), line, fill=(241, 245, 249, 255), font=font)
    text_y += body_line_height

img.save(image_path, "PNG")

# --- 7. Download and Standardize Stock Audio Track ---
raw_audio_path = "raw_music.ogg"
audio_path = "background_music.mp3"
video_path = "temp_reel_video.mp4"

print("Downloading stock music track...")
music_url = "https://upload.wikimedia.org/wikipedia/commons/e/e4/Scott_Joplin_-_Easy_Winners_%281901%29.ogg"
headers = {
    "User-Agent": "DailyScoopBot/1.0 (Contact: admin@dailyscoop.local; Automated educational media project)"
}

try:
    music_res = requests.get(music_url, headers=headers, timeout=20)
    music_res.raise_for_status()
    with open(raw_audio_path, "wb") as f:
        f.write(music_res.content)
    
    print("Standardizing audio track to MP3...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", raw_audio_path,
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        audio_path
    ], check=True)
    print("Audio standardization complete.")
except Exception as e:
    print(f"Warning: Stock audio download/conversion failed ({e}). Creating silent fallback track.")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "6", audio_path], check=True)

# --- 8. Combine Image and Audio with Explicit Stream Mapping ---
print("Combining image and standardized audio into 1080x1920 6-second MP4 video...")
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-i", image_path,
    "-i", audio_path,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-c:v", "libx264",
    "-tune", "stillimage",
    "-t", "6",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",
    video_path
]

subprocess.run(ffmpeg_cmd, check=True)
print("Video reel created successfully with locked-in audio stream.")

# --- 9. Format Social Media Caption Text ---
post_header = make_bold("🍦 THE DAILY ICE CREAM REEL WITH PETEY & ANDREW 🐾\n\n")
engagement_cta = (
    "\n\n" + "🐕 " + make_bold("LAB TESTED & APPROVED!") + "\n" +
    "Andrew and Petey checked the data logs on this one. What's your top flavor? Drop it below! 👇"
)
post_text = post_header + ai_trivia_formatted + engagement_cta

# --- 10. Post Video to Facebook Reels (Sharing to both Reels Tab & Main Feed) ---
page_id = os.environ["FACEBOOK_PAGE_ID"]
active_token = get_valid_facebook_token()
post_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"

with open(video_path, "rb") as vid_file:
    files = {"source": vid_file}
    payload = {
        "description": post_text,
        "media_type": "REELS",
        "share_to_feed": "true",
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
