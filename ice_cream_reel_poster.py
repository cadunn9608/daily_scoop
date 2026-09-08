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
            past_words = set(w for w in past.lower().split() if len(w) > 4)
            candidate_words = set(w for w in candidate_lower.split() if len(w) > 4)
            common_words = past_words.intersection(candidate_words)
            if len(common_words) >= 3:
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

# --- 2. Generate Vertical 9:16 Background Image (Cleaned of Background Signs/Text) ---
image_prompts_pool = [
    "A stunning 9:16 vertical 3D Pixar-style digital art piece featuring Andrew, a fluffy golden retriever puppy, and Petey, an all-white puppy with a black eye patch, running a turn-of-the-century horse-drawn ice cream wagon on a bustling 1900 cobblestone New York street. No readable background text or signs. Vibrant colors, cinematic vertical composition.",
    "A whimsical 9:16 vertical 3D Disney-style digital art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, operating a gleaming Victorian ice cream parlor with stained glass windows and polished brass fixtures. Clean background with no text. Warm cinematic lighting, ultra-detailed.",
    "A magical 9:16 vertical 3D Pixar-style art piece showing Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, serving towering waffle cones at a glowing 1900s world's fair ice cream pavilion under striped canvas tents. Clean background architecture with no letters or words. Vibrant and detailed.",
    "A charming 9:16 vertical 3D Disney-style digital art piece with Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, mixing colorful ice cream sodas behind a mahogany counter in a cozy 1905 apothecary soda fountain. No background signs or text. Warm vintage colors.",
    "An enchanted 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, serving steaming hot fudge sundaes inside a cozy winter chalet in 1910 by a glowing stone fireplace. Clean interior design with no letters. Cinematic lighting.",
    "A bright 9:16 vertical 3D Disney-style digital art piece showing Andrew, a fluffy golden retriever puppy, and Petey, an all-white puppy with a black eye patch, wearing sailor caps at a 1920s seaside boardwalk ice cream stand as colorful waves crash behind them. No signs or text. Vibrant summer colors.",
    "A whimsical 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, operating a steampunk ice cream factory filled with copper pipes and swirling vanilla soft-serve while wearing tiny goggles. Ultra-detailed, no text.",
    "A classic 9:16 vertical 3D Disney-style art piece showing Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, standing by a 1900 soda shop counter decorated with vintage glass sprinkle jars and bowties. Clean background with no text. Warm nostalgic lighting.",
    "A magical 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, at a night-time carnival ice cream cart lit by thousands of glowing fairy lights, handing out treats. No signs. Vibrant colors.",
    "A charming 9:16 vertical 3D Disney-style digital art piece showing Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, serving homemade churned ice cream in wooden bowls on a rustic old-fashioned country store porch in 1902. Clean wooden architecture with zero text.",
    "A grand 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, presenting an elaborate multi-tiered ice cream cake in a majestic 1910 grand hotel dessert salon. Elegant background with no letters. Cinematic lighting.",
    "A whimsical 9:16 vertical 3D Disney-style art piece showing Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, wearing tiny diving helmets inside an underwater coral-reef ice cream parlor scooping pastel treats. Clean coral backdrop. Vibrant aquatic colors.",
    "A glowing 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, inside an enchanted forest treehouse ice cream shoppe surrounded by sparkling mint-chip swirls and fireflies. Magical lighting, no text.",
    "A bustling 9:16 vertical 3D Disney-style art piece showing Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, at a 1908 railway station ice cream kiosk with clean architectural pillars and no signs. Warm vintage afternoon sun.",
    "A vintage 9:16 vertical 3D Pixar-style art piece featuring Andrew, a golden retriever puppy, and Petey, an all-white puppy with a black eye patch, managing a 1920s jazz-age rooftop ice cream lounge under starlit skies and glowing string lights. Clean city backdrop with no text. Cinematic mood."
]

image_prompt = random.choice(image_prompts_pool)
print("Selected random background prompt theme for this run.")

image_bytes = None
image_models_to_try = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-image-preview"
]

for img_model in image_models_to_try:
    try:
        response = client.models.generate_content(model=img_model, contents=image_prompt)
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break
            if image_bytes:
                break
        if image_bytes:
            print(f"Successfully generated background image using model: {img_model}")
            break
    except Exception:
        time.sleep(2)

if not image_bytes:
    raise Exception("All image models failed for Reel background generation.")

# --- 3. Process Image and Overlay Top-Positioned Text Box (Moved up higher to Y = 50) ---
image_path_png = "temp_reel_image.png"
img = Image.open(BytesIO(image_bytes)).convert("RGBA")
img_width, img_height = img.size

body_font_size = 25
line_height = 36

try:
    font = ImageFont.truetype("DejaVuSans.ttf", body_font_size)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 29)
except IOError:
    font = ImageFont.load_default()
    header_font = font

box_x0 = 60
box_x1 = img_width - 60
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
    wrapped_lines.append("")

if wrapped_lines and wrapped_lines[-1] == "":
    wrapped_lines.pop()

padding = 28
total_box_height = (len(wrapped_lines) * line_height) + (padding * 2)

# Moved up higher to Y = 50 (~0.5" higher than previous 90 position)
box_y0 = 50
box_y1 = box_y0 + total_box_height

overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw_overlay = ImageDraw.Draw(overlay)
draw_overlay.rounded_rectangle(
    [box_x0, box_y0, box_x1, box_y1],
    radius=24,
    fill=(15, 23, 42, 240),      # Rich dark navy background
    outline=(245, 158, 11, 255),  # Warm amber/gold border
    width=5
)

img = Image.alpha_composite(img, overlay).convert("RGB")
draw = ImageDraw.Draw(img)

text_x = box_x0 + 25
text_y = box_y0 + padding

for i, line in enumerate(wrapped_lines):
    if line == "":
        text_y += line_height // 2
        continue
    
    if i == 0:
        draw.text((text_x + 2, text_y + 2), line, fill=(0, 0, 0, 180), font=header_font)
        draw.text((text_x, text_y), line, fill=(252, 211, 77, 255), font=header_font)
    else:
        draw.text((text_x + 2, text_y + 2), line, fill=(0, 0, 0, 180), font=font)
        draw.text((text_x, text_y), line, fill=(241, 245, 249, 255), font=font)
        
    text_y += line_height

img.save(image_path_png, "PNG")

# --- 4. Fetch Reliable MP3 Audio & Render MP4 Video via Robust FFmpeg Pipeline ---
audio_path = "temp_music.mp3"
# Direct, reliable public domain MP3 audio link (Scott Joplin ragtime piano)
reliable_audio_url = "https://ia800504.us.archive.org/3/items/TheEntertainerScottJoplin1902/TheEntertainer.mp3"

audio_downloaded = False
try:
    audio_res = requests.get(reliable_audio_url, timeout=15)
    if audio_res.status_code == 200:
        with open(audio_path, "wb") as f:
            f.write(audio_res.content)
        audio_downloaded = True
        print("Successfully downloaded upbeat ragtime MP3 music track!")
except Exception as e:
    print(f"Warning: Could not download background music ({e}), using synthetic tone generator fallback.")

video_path_mp4 = "temp_reel_video.mp4"

if audio_downloaded:
    # Explicit stream mapping (-map 0:v:0 -map 1:a:0) ensures Facebook recognizes the valid audio track
    ffmpeg_cmd = [
        "ffmpeg", "-loop", "1", "-i", image_path_png,
        "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-t", "6", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-shortest", "-y", video_path_mp4
    ]
else:
    # Bulletproof fallback using FFmpeg's built-in synth generator so it never registers as silent
    ffmpeg_cmd = [
        "ffmpeg", "-loop", "1", "-i", image_path_png,
        "-f", "lavfi", "-i", "sine=f=440:d=6",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-t", "6", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-shortest", "-y", video_path_mp4
    ]

subprocess.run(ffmpeg_cmd, check=True)
print("Reel video and background music rendered successfully with active audio track!")

# --- 5. Publish to Facebook Reels API with Correct Binary Upload ---
page_id = os.environ["FACEBOOK_PAGE_ID"]
access_token = get_valid_facebook_token()

start_url = f"https://graph.facebook.com/v18.0/{page_id}/video_reels?upload_phase=start&access_token={access_token}"
start_res = requests.post(start_url).json()

if "error" in start_res:
    raise Exception(f"Facebook Reels API initialization failed: {start_res}")

video_id = start_res.get("video_id")
upload_url = start_res.get("upload_url")

if not video_id or not upload_url:
    raise Exception(f"Facebook Reels API returned missing video_id or upload_url: {start_res}")

file_size = os.path.getsize(video_path_mp4)
headers = {
    "Authorization": f"OAuth {access_token}",
    "offset": "0",
    "file_size": str(file_size)
}
with open(video_path_mp4, "rb") as video_file:
    upload_res = requests.post(upload_url, data=video_file.read(), headers=headers).json()

if "error" in upload_res:
    raise Exception(f"Facebook binary video file upload failed: {upload_res}")

caption = "🍦 " + make_bold("DAILY ICE CREAM REEL") + "\n\n" + make_bold(cleaned_trivia) + "\n\n🐾 Andrew & Petey's Sweet Scoop! What's your top flavor? 👇 #IceCream #Reels #Trivia"
finish_url = f"https://graph.facebook.com/v18.0/{page_id}/video_reels"
finish_params = {
    "upload_phase": "finish",
    "video_id": video_id,
    "video_state": "PUBLISHED",
    "description": caption,
    "access_token": access_token
}

finish_res = requests.post(finish_url, data=finish_params).json()

if "error" in finish_res or not finish_res.get("success", False):
    raise Exception(f"Facebook Reel publishing failed during finish phase: {finish_res}")

print(f"Successfully published Facebook Reel! Video ID: {video_id}")
