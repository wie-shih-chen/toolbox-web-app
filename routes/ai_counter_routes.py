from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from google import genai
import io
from PIL import Image

ai_counter_bp = Blueprint('ai_counter', __name__)

@ai_counter_bp.route('/')
@login_required
def index():
    return render_template('ai_counter/index.html')

@ai_counter_bp.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': '請上傳圖片'}), 400
        
    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'error': '請選擇圖片'}), 400
        
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    if not gemini_key:
        return jsonify({'error': '系統未設定 Gemini API 金鑰'}), 500
        
    try:
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        
        client = genai.Client(api_key=gemini_key)
        prompt = "你是一個幫助使用者計數與分析圖片內容的 AI 小幫手。請幫我仔細算算這張圖片裡有幾顆藥丸（或其他物品）？請先簡短說明你看到了什麼，然後給出一個精確的數量。"
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[prompt, img]
        )
        
        return jsonify({'result': response.text.strip()})
    except Exception as e:
        current_app.logger.error(f"[AI Counter] 分析失敗: {e}")
        return jsonify({'error': f'分析失敗: {e}'}), 500
