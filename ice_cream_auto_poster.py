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

# 1. Fully Dynamic Topic Generation (Guarantees zero repeats by having AI invent a fresh, random topic every time)
trivia_prompt = (
    "Generate a completely random, fascinating, and unique ice cream trivia fact (maximum 3 short sentences total). "
    "To ensure variety, choose a completely unexpected angle—it could be an obscure historical event, a bizarre ancient or modern flavor, "
    "a fascinating food science principle, a global cultural tradition, or a modern culinary trend from 1990 onward. "
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
    print(f"Attempting dynamic trivia generation using model: {model_name}")
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

header_tag = "★ DAILY ICE CREAM TRIVIA ★"
ai_trivia_formatted = make_bold(cleaned_trivia)

# 2. Randomized Cartoon Background Settings Pool (33+ Options)
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

# 3. Randomized Scientist, Engineer, and Master Chef Roles & Actions
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

image_prompt = (
    f"A high-end 3D animated digital art piece in the distinct visual style of Pixar and Disney, "
    f"featuring Andrew the golden retriever puppy and Petey, a loyal white-and-black pit bull mix with a distinct black patch over his left eye, "
    f"working together inside {setting_choice}. "
    f"They are {character_action_choice}. "
    "Vibrant warm lighting, charming characters, polished cinematic digital rendering, perfect composition."
)

print(f"Generating cartoon background image with prompt: {image_prompt}")

image_bytes = None
image_models_to_try = ["gemini-3.1-flash-image", "gemini-3.1-flash-image-preview"]

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

# 4. Process Image & Render Pixel-Perfect Text Box Overlay
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

# 5. Format Social Media Caption Text
post_header = make_bold("🍦 THE DAILY SCOOP WITH PETEY & ANDREW 🐾\n\n")
engagement_cta = (
    "\n\n" + "🐕 " + make_bold("QUALITY CONTROL APPROVED!") + "\n" +
    "Andrew and Petey reviewed today's data from the lab and gave it two paws up. " +
    "What flavor are you tasting today? Let us know below! 👇"
)
post_text = post_header + ai_trivia_formatted + engagement_cta

# 6. Exchange/Refresh Facebook Token
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

# 7. Post the Branded Photo + Caption to Facebook Page Feed (Fixed graph.facebook.com URL)
page_id = os.environ["FACEBOOK_PAGE_ID"]
post_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"

with open(image_path, "rb") as img_file:
    files = {"source": img_file}
    payload = {
        "caption": post_text,
        "published": "true",
        "access_token": active_token
    }
    res = requests.post(post_url, data=payload, files=files)
    print("Facebook Photo Post Response:", res.json())
