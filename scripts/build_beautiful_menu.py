import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def get_image_from_url(url, size):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = img.resize(size, Image.Resampling.LANCZOS)
    return img

def create_beautiful_menu(filename="rich_menu.jpg"):
    # Size for 3 tabs
    W, H = 2500, 843
    
    # Create white background
    img = Image.new('RGBA', (W, H), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Download icons
    print("Downloading icons...")
    icon1 = get_image_from_url("https://img.icons8.com/color/512/wallet.png", (220, 220))
    icon2 = get_image_from_url("https://img.icons8.com/color/512/calendar--v1.png", (220, 220))
    icon3 = get_image_from_url("https://img.icons8.com/color/512/help.png", (220, 220))
    
    # Draw soft dividers
    divider_color = (230, 235, 240, 255)
    draw.line([(833, 100), (833, 743)], fill=divider_color, width=4)
    draw.line([(1666, 100), (1666, 743)], fill=divider_color, width=4)
    
    # Font setup
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 110)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 110)
        except:
            font = ImageFont.load_default()
            
    # Draw Cell 1 (Expense)
    img.alpha_composite(icon1, (306, 200))
    draw.text((200, 480), "快速記帳", fill=(60, 64, 67, 255), font=font)
    
    # Draw Cell 2 (Shift)
    img.alpha_composite(icon2, (1139, 200))
    draw.text((1033, 480), "新增排班", fill=(60, 64, 67, 255), font=font)
    
    # Draw Cell 3 (Settings/Help)
    img.alpha_composite(icon3, (1972, 200))
    draw.text((1866, 480), "查看說明", fill=(60, 64, 67, 255), font=font)
    
    # Add top colored bar for accent (like the screenshot)
    draw.rectangle([0, 0, W, 20], fill=(70, 160, 255, 255))
    
    # Convert to RGB to save as JPG
    rgb_img = img.convert('RGB')
    
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    rgb_img.save(filepath, quality=95)
    print(f"Saved image to {filepath}")
    return filepath

if __name__ == '__main__':
    create_beautiful_menu()
