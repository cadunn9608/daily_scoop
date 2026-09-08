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
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
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
        "Draw from a mix of categories: Celebrities & Famous Figures (e.g., favorite brands or anecdotes), "
        "Brand Origin Stories (e.g., unexpected roadblocks or naming inspirations), or Inventions & Firsts (e.g., iconic novelties or serving methods of the era). "
        "CRITICAL FIT REQUIREMENT: Keep the entire text concise (UNDER 30 WORDS / maximum 2 short sentences) so it fits inside a mobile video overlay box. "
        "Do not include boring or purely numerical statistic questions. "
        f"{history_exclusion} "
        "Output only the trivia content without any Markdown formatting or emojis."
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
prefixes_to_strip = ["ice cream trivia:", "did you know:", "trivia fact:", "fun fact:", "fact:"]
for p in prefixes_to_strip:
    if cleaned_trivia.lower().startswith(p):
        cleaned_trivia = cleaned_trivia[len(p):].strip()
        break

with open(history_file, "a", encoding="utf-8") as f:
    f.write(cleaned_trivia + "\n")
print("Saved new unique reel trivia fact to reel_history.txt")

# --- 2. Generate Vertical 9:16 Background Image with Working Models ---
image_prompt = (
    "A stunning 9:16 vertical aspect ratio 3D animated digital art piece in the style of Pixar and Disney, "
    "featuring Andrew, a fluffy golden retriever puppy, and Petey, an all-white puppy with a black eye patch, "
    "running a vibrant, magical gourmet ice cream shoppe filled with glowing neon lights and swirling soft-serve machines. "
    "Vibrant colors, cinematic vertical composition, ultra-detailed."
)

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

# --- 3. Process Image and Overlay Clean Safe-Zone Text Box ---
image_path_png = "temp_reel_image.png"
img = Image.open(BytesIO(image_bytes)).convert("RGBA")
img_width, img_height = img.size

# Determine font size dynamically based on length to guarantee it fits safely
text_length = len(cleaned_trivia)
if text_length > 180:
    body_font_size = 20
    header_font_size = 24
    line_height = 28
elif text_length > 120:
    body_font_size = 22
    header_font_size = 26
    line_height = 30
else:
    body_font_size = 24
    header_font_size = 28
    line_height = 34

try:
    font = ImageFont.truetype("DejaVuSans.ttf", body_font_size)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", header_font_size)
except IOError:
    font = ImageFont.load_default()
    header_font = font

# Horizontal margins keep text away from video edges
box_x0 = 70
box_x1 = img_width - 70
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

header_height = 40
padding = 24
total_box_height = header_height + (len(wrapped_lines) * line_height) + (padding * 2)

# Position the bottom of the box above the Reel UI caption safe zone (320px from bottom)
box_y1 = img_height - 320
box_y0 = box_y1 - total_box_height

# Make sure box top does not invade top navigation UI safe area (minimum top margin 220px)
if box_y0 < 220:
    box_y0 = 220
    box_y1 = box_y0 + total_box_height

overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw_overlay = ImageDraw.Draw(overlay)
draw_overlay.rounded_rectangle(
    [box_x0, box_y0, box_x1, box_y1],
    radius=20,
    fill=(15, 23, 42, 235),
    outline=(245, 158, 11, 255),
    width=4
)

img = Image.alpha_composite(img, overlay).convert("RGB")
draw = ImageDraw.Draw(img)

text_x = box_x0 + 25
text_y = box_y0 + padding

draw.text((text_x, text_y), "★ ICE CREAM REEL TRIVIA ★", fill=(252, 211, 77, 255), font=header_font)
text_y += header_height

for line in wrapped_lines:
    draw.text((text_x, text_y), line, fill=(241, 245, 249, 255), font=font)
    text_y += line_height

img.save(image_path_png, "PNG")

# --- 4. Convert PNG to MP4 Video via FFmpeg ---
video_path_mp4 = "temp_reel_video.mp4"
ffmpeg_cmd = [
    "ffmpeg", "-loop", "1", "-i", image_path_png,
    "-c:v", "libx264", "-t", "6", "-pix_fmt", "yuv420p",
    "-vf", "scale=1080:1920", "-y", video_path_mp4
]
subprocess.run(ffmpeg_cmd, check=True)
print("Reel video rendered successfully!")

# --- 5. Publish to Facebook Reels API with Correct Binary Upload ---
page_id = os.environ["FACEBOOK_PAGE_ID"]
access_token = get_valid_facebook_token()

# Step 1: Initialize upload
start_url = f"https://graph.facebook.com/v18.0/{page_id}/video_reels?upload_phase=start&access_token={access_token}"
start_res = requests.post(start_url).json()

if "error" in start_res:
    raise Exception(f"Facebook Reels API initialization failed: {start_res}")

video_id = start_res.get("video_id")
upload_url = start_res.get("upload_url")

if not video_id or not upload_url:
    raise Exception(f"Facebook Reels API returned missing video_id or upload_url: {start_res}")

# Step 2: Upload binary video stream with correct headers
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

# Step 3: Finish and Publish
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
