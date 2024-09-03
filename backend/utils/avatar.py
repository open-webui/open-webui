from PIL import Image, ImageDraw, ImageFont
import base64
import io

def create_avatar(initials, size=130, bg_color=(240, 173, 78), text_color=(255, 255, 255)):
    image = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(image)
    
    font_size = int(size / 2)
    try:
        font = ImageFont.truetype("Arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    
    left, top, right, bottom = draw.textbbox((0, 0), initials, font=font)
    text_width = right - left
    text_height = bottom - top
    position = ((size - text_width) / 2, (size - text_height) / 2 - top / 2)
    
    draw.text(position, initials, font=font, fill=text_color)
    
    return image

def save_avatar_to_file(avatar, filename="avatar.png"):
    avatar = avatar.resize((64, 64), Image.Resampling.LANCZOS)
    avatar.save(filename)
    print(f"Avatar saved as {filename}")

def avatar_to_base64(avatar):
    avatar = avatar.resize((64, 64), Image.Resampling.LANCZOS)
    buffered = io.BytesIO()
    avatar.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def generate_avatar(first_name, last_name):

    initials = f"{first_name[0]}{last_name[0]}"
    avatar = create_avatar(initials)

    img_str = avatar_to_base64(avatar)
    return f"data:image/png;base64,{img_str}"