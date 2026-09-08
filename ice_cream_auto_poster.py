import os
import time
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

def make_bold(text):
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    return text.translate(str.maketrans(normal, bold))

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 1. Randomized Ice Cream Trivia Categories to Ensure Unique Daily Content
trivia_categories = [
    "historical origins of ice cream and presidential recipes",
    "bizarre and unusual historical ice cream flavors",
    "ice cream food science and freezing point depression",
    "global ice cream traditions and unique international styles",
    "fun manufacturing and production milestones through history",
    "classic ice cream parlour inventions and sundae folklore"
]
selected_category = random.choice(trivia_categories)

trivia_prompt = (
    f"Create a fascinating, highly engaging daily ice cream trivia fact (maximum 3 short sentences total) "
    f"focused on: {selected_category}. "
    "Do not mention any commercial brand names like Dr. Bombay or Zumper. "
    "Output only the trivia content without any Markdown formatting or emojis."
)

ai_trivia_raw = None
text_models_to_try = [
    "gemini-3.5-flash",
    "gemini-3.1-flash",
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite"
]

for model_name in text_models_to_try:
    print(f"Attempting trivia generation using model: {model_name}")
    try:
        response_text = client.models.generate_content(
            model=model_name,
            contents=trivia_prompt,
        )
        ai_trivia_raw = response_text.text.strip()
        print(f"Successfully generated trivia using {model_name}!")
        break
    except Exception as e:
        print(f"Model {model_name} failed with error: {e}. Trying next...")
        time.sleep(5)

if not ai_trivia_raw:
    raise Exception("All models failed to generate trivia content due to high demand.")

# Clean up redundant prefixes case-insensitively
cleaned_trivia = ai_trivia_raw
prefixes_to_strip = [
    "ice cream trivia:", "did you know:", "trivia fact:", "fun fact:",
    "ice cream fact", "trivia", "fact:"
]
lower_trivia = cleaned_trivia.lower()
for p in prefixes_to_strip:
    if lower_trivia.startswith(p):
        cleaned_trivia = cleaned_trivia[len(p):].strip()
        break

header_tag = "🍦 DAILY ICE CREAM TRIVIA 🐾"
ai_trivia_formatted = make_bold(cleaned_trivia)

# 2. Cartoon Background Generation Prompt featuring Petey & Andrew in a Lab Setting
setting_choice = random.choice([
    "a high-tech futuristic ice cream testing laboratory with glowing holographic flavor charts and stainless steel tasting counters",
    "a cozy, sunlit wooden workshop filled with vintage ice cream churns, recipe notebooks, and colorful ingredient jars",
    "a whimsical modern kitchen workspace with digital flavor analysis screens and bubbling test tubes of sweet syrups"
])

image_prompt = (
    f"A high-end 3D animated digital art piece in the distinct visual style of Pixar and Disney, "
    f"featuring Andrew the golden retriever puppy and Petey, a loyal white-and-black pit bull mix with a distinct black patch over his left eye, "
    f"working together inside {setting_choice}. "
    "They are wearing tiny tasting chef hats, examining ice cream samples with playful expressions. "
    "Vibrant warm lighting, charming characters, polished cinematic digital rendering, perfect composition."
)

print(f"Generating cartoon background image with prompt: {image_prompt}")

image_bytes = None
image_models_to_try = ["gemini-2.5-flash", "gemini-3.1-flash-image", "gemini-3.1-flash-image-preview"]

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
            print(f"Successfully generated background image using model: {img_model}")
            break
    except Exception as e:
        print(f"Image model {img_model} failed: {e}. Trying next...")

if not image_bytes:
    raise Exception("All Gemini image generation models failed to return image data.")

image_path = "temp_trivia_image.png"

# 3. Process Image & Render Pixel-Perfect Text Box Overlay
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

box_y1 = img_height - 30
box_y0 = box_y1 - total_box_height

overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
draw_overlay = ImageDraw.Draw(overlay)

draw_overlay.rounded_rectangle(
    [box_x0, box_y0, box_x1, box_y1], 
    radius=16, 
    fill=(15, 23, 42, 235), 
    outline=(245, 158, 11, 255),  # Warm amber border for ice cream theme
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
print("Trivia background image with clean text overlay successfully generated and saved!")

# 4. Format Social Media Caption Text
post_header = make_bold("🍦 THE DAILY SCOOP WITH PETEY & ANDREW 🐾\n\n")
engagement_cta = (
    "\n\n" + "🐕 " + make_bold("QUALITY CONTROL APPROVED!") + "\n" +
    "Andrew and Petey reviewed today's data from the lab and gave it two paws up. " +
    "What flavor are you tasting today? Let us know below! 👇"
)
post_text = post_header + ai_trivia_formatted + engagement_cta

# 5. Exchange/Refresh Facebook Token
app_id = os.environ["FACEBOOK_APP_ID"]
app_secret = os.environ["FACEBOOK_APP_SECRET"]
current_token = os.environ["FACEBOOK_ACCESS_TOKEN"]

refresh_url = "https://graph.facebook.com/v18.0/oauth/access_token"
refresh_params = {
    "grant_type": "fb_exchange_token",
    "client_id": app_id,
    "client_secret": app_secret,
    "fb_exchange_token": current_token
}
refresh_res = requests.get(refresh_url, params=refresh_params).json()
active_token = refresh_res.get("access_token", current_token)

# 6. Post the Branded Photo + Caption to Facebook Page Feed
page_id = os.environ["FACEBOOK_PAGE_ID"]
post_url = f"https://graph.facebook.0/v18.0/{page_id}/photos" if False else f"https://graph.facebook.com/v18.0/{page_id}/photos"

with open(image_path, "rb") as img_file:
    files = {"source": img_file}
    payload = {
        "caption": post_text,
        "published": "true",
        "access_token": active_token
    }
    res = requests.post(post_url, data=payload, files=files)
    print("Facebook Photo Post Response:", res.json())
