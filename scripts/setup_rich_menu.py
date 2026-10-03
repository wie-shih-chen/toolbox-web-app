import os
import sys
from dotenv import load_dotenv

# 讀取 .env (由於在 web_app/scripts，我們先往上一層找)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(parent_dir, '.env'))

from build_beautiful_menu import create_beautiful_menu as create_rich_menu_image

if __name__ == '__main__':
    from linebot import LineBotApi
    from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, PostbackAction
    
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
                action=PostbackAction(
                    label='快速記帳', 
                    data='action=start_expense', 
                    display_text='我要記帳',
                    input_option='openKeyboard',
                    fill_in_text='記帳 '
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                action=PostbackAction(
                    label='新增排班', 
                    data='action=start_shift', 
                    display_text='我要排班',
                    input_option='openKeyboard',
                    fill_in_text='排班 '
                )
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                action=PostbackAction(
                    label='查看說明', 
                    data='action=help',
                    display_text='說明'
                )
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
