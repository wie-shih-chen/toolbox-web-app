from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from google import genai
import io, json
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
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        img_w, img_h = img.size
        
        output_io = io.BytesIO()
        img.save(output_io, format='JPEG', quality=85)
        compressed_bytes = output_io.getvalue()
        
        from google.genai import types
        image_part = types.Part.from_bytes(data=compressed_bytes, mime_type='image/jpeg')
        
        client = genai.Client(api_key=gemini_key)

        # 請 Gemini 回傳每個物件的 bounding box（normalized 0~1000）
        prompt = """請仔細辨識這張圖片中的所有物件（例如藥丸、零件、水果等）。
對每一個可辨識的物件，輸出其標準化邊框座標（範圍 0~1000，左上角為 0,0）。

請只回傳以下格式的 JSON，不要有任何說明文字或 markdown：
{
  "objects": [
    {"box": [ymin, xmin, ymax, xmax]},
    ...
  ],
  "total": 數量
}

注意：
- box 格式為 [ymin, xmin, ymax, xmax]，值域均為 0~1000
- objects 陣列長度必須等於 total
- 若物件太多（超過 200 個），抽樣計數並在 total 填入估計總數即可"""
        
        import time
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=[prompt, image_part]
                )
                break
            except Exception as e:
                if '503' in str(e) and attempt < 2:
                    time.sleep(2)
                    continue
                raise e
        
        raw = response.text.strip()
        # 清理 markdown 包裝
        if '```' in raw:
            parts = raw.split('```')
            raw = parts[1] if len(parts) > 1 else parts[0]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        return jsonify({
            'objects': parsed.get('objects', []),
            'total':   parsed.get('total', 0),
            'img_w':   img_w,
            'img_h':   img_h,
        })

    except Exception as e:
        current_app.logger.error(f"[AI Counter] 分析失敗: {e}")
        return jsonify({'error': f'分析失敗: {e}'}), 500
