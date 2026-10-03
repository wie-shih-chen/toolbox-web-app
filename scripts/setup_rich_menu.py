import os
import sys
from dotenv import load_dotenv

# 讀取 .env (由於在 web_app/scripts，我們先往上一層找)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(parent_dir, '.env'))

def create_rich_menu_image(filename="rich_menu.jpg"):
    from PIL import Image, ImageDraw, ImageFont
    
    # 建立 2500x843 的圖片 (LINE Rich Menu 推薦尺寸 3欄)
    img = Image.new('RGB', (2500, 843), color=(240, 245, 250))
    draw = ImageDraw.Draw(img)
    
    # 畫框線
    draw.line([(833, 0), (833, 843)], fill=(200, 200, 200), width=6)
    draw.line([(1666, 0), (1666, 843)], fill=(200, 200, 200), width=6)
    
    # 字體
    try:
        font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 130)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 130)
        except:
            font = ImageFont.load_default()
            
    # 文字置中 (每格寬度 833，文字大概寬 520)
    draw.text((150, 340), "快速記帳", fill=(50, 50, 50), font=font)
    draw.text((983, 340), "新增排班", fill=(50, 50, 50), font=font)
    draw.text((1816, 340), "查看說明", fill=(50, 50, 50), font=font)
    
    filepath = os.path.join(current_dir, filename)
    img.save(filepath, quality=95)
    return filepath

if __name__ == '__main__':
    from linebot import LineBotApi
    from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, MessageAction
    
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not token:
        print("❌ 未設定 LINE_CHANNEL_ACCESS_TOKEN")
        sys.exit(1)
        
    line_bot_api = LineBotApi(token)
    
    # 1. 建立 Rich Menu Object
    rich_menu_to_create = RichMenu(
        size=RichMenuSize(width=2500, height=843),
        selected=True,
        name="工具箱主選單",
        chat_bar_text="打開選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=MessageAction(label='快速記帳', text='我要記帳')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                action=MessageAction(label='新增排班', text='我要排班')
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                action=MessageAction(label='查看說明', text='說明')
            )
        ]
    )
    
    try:
        print("1. 建立選單中...")
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
        print(f"✅ Created Rich Menu ID: {rich_menu_id}")
        
        print("2. 產生並上傳圖片中...")
        img_path = create_rich_menu_image()
        with open(img_path, 'rb') as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/jpeg", f)
        print("✅ 圖片上傳成功")
            
        print("3. 設定為預設選單...")
        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ 成功！用戶現在應該可以看到底部選單了。")
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
