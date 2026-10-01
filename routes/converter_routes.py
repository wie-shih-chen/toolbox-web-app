import os
import shutil
import uuid
import zipfile
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from services.converter_service import ConverterService

converter_bp = Blueprint('converter', __name__, url_prefix='/converter')

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

ALLOWED_EXTS = ConverterService.ALL_ALLOWED_EXTS

def _allowed(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTS

def _get_download_dir() -> str:
    base = current_app.config.get('DOWNLOAD_PATH', '/tmp')
    d = os.path.join(base, 'converter')
    os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #

@converter_bp.route('/')
@login_required
def index():
    return render_template('converter/index.html')


@converter_bp.route('/convert', methods=['POST'])
@login_required
def convert():
    """
    Main conversion endpoint.
    form fields:
      - file         : uploaded file
      - task         : 'doc_convert' | 'pdf_unlock' | 'pdf_compress' | 'img_convert' | 'pdf_to_img'
      - target_fmt   : output format string (when task == 'doc_convert' or 'img_convert')
      - password     : PDF password (when task == 'pdf_unlock')
      - quality      : 'low'|'medium'|'high' (when task == 'pdf_compress')
      - img_quality  : 1-100 (when task == 'img_convert')
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '請選擇要上傳的檔案'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'success': False, 'error': '未收到檔案'}), 400

    if not _allowed(f.filename):
        return jsonify({'success': False, 'error': '不支援的檔案格式'}), 400

    # Check file size (read into memory first — PythonAnywhere safe for ≤32MB)
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    if size > ConverterService.MAX_FILE_SIZE:
        return jsonify({'success': False, 'error': f'檔案超過 32 MB 限制 (目前：{ConverterService.human_size(size)})'}), 400

    task        = request.form.get('task', 'doc_convert')
    target_fmt  = request.form.get('target_fmt', 'pdf').lower().strip('.')
    password    = request.form.get('password', '')
    doc_password = request.form.get('doc_password', '')   # for encrypted Office files
    quality     = request.form.get('quality', 'medium')
    img_quality = int(request.form.get('img_quality', 85))

    # Save upload to temp dir
    tmp_dir = ConverterService._tmp_dir()
    try:
        safe_name = ConverterService._safe_filename(f.filename)
        src_path  = os.path.join(tmp_dir, safe_name)
        f.save(src_path)

        orig_ext  = ConverterService._ext(f.filename)
        orig_stem = os.path.splitext(f.filename)[0]   # original filename without extension
        out_path  = None

        # ── Task routing ── #

        if task == 'pdf_unlock':
            if orig_ext != '.pdf':
                return jsonify({'success': False, 'error': '解密功能只支援 PDF 檔案'}), 400
            if not password:
                return jsonify({'success': False, 'error': '請輸入 PDF 密碼'}), 400
            out_path = ConverterService.pdf_unlock(src_path, password, tmp_dir)

        elif task == 'pdf_compress':
            if orig_ext != '.pdf':
                return jsonify({'success': False, 'error': '壓縮功能只支援 PDF 檔案'}), 400
            out_path = ConverterService.pdf_compress(src_path, quality, tmp_dir)

        elif task == 'pdf_to_img':
            if orig_ext != '.pdf':
                return jsonify({'success': False, 'error': 'PDF 轉圖片只支援 PDF 輸入'}), 400
            fmt = target_fmt if target_fmt in ('png', 'jpg', 'jpeg') else 'png'
            pages = ConverterService.pdf_to_images(src_path, tmp_dir, fmt=fmt)
            if not pages:
                return jsonify({'success': False, 'error': 'PDF 轉圖片未產生任何輸出'}), 500

            if len(pages) == 1:
                out_path = pages[0]
            else:
                # Bundle multiple pages into a ZIP
                zip_path = os.path.join(tmp_dir, 'pages.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for p in pages:
                        zf.write(p, os.path.basename(p))
                out_path = zip_path

        elif task == 'img_convert':
            if orig_ext not in ConverterService.IMAGE_INPUT_EXTS:
                return jsonify({'success': False, 'error': '圖片轉換只支援圖片格式輸入'}), 400
            out_path = ConverterService.convert_image(src_path, target_fmt, tmp_dir, quality=img_quality)

        elif task == 'img_to_pdf':
            if orig_ext not in ConverterService.IMAGE_INPUT_EXTS:
                return jsonify({'success': False, 'error': '圖片轉 PDF 只支援圖片格式輸入'}), 400
            out_path = ConverterService.image_to_pdf(src_path, tmp_dir)

        else:
            # doc_convert — supports PDF or Office docs
            out_path = ConverterService.doc_to_format(src_path, target_fmt, tmp_dir,
                                                      password=doc_password)

        if not out_path or not os.path.exists(out_path):
            return jsonify({'success': False, 'error': '轉換失敗：未產生輸出檔案'}), 500

        # ── Build friendly output filename: original_name_targetfmt.ext ── #
        out_ext = os.path.splitext(out_path)[1]  # extension from LibreOffice/Ghostscript output
        fmt_label = out_ext.lstrip('.').upper()
        friendly_name = f"{orig_stem}_{fmt_label}{out_ext}"

        # Move output to stable downloads folder so send_file works
        dl_dir     = _get_download_dir()
        token      = uuid.uuid4().hex          # random token to avoid collisions
        final_name = f"{token}_{friendly_name}"
        final_path = os.path.join(dl_dir, final_name)
        shutil.move(out_path, final_path)

        orig_size   = ConverterService.human_size(size)
        output_size = ConverterService.human_size(os.path.getsize(final_path))

        return jsonify({
            'success': True,
            'download_url': url_for('converter.download', filename=final_name),
            'filename': friendly_name,
            'orig_size': orig_size,
            'output_size': output_size,
        })

    except ValueError as e:
        if str(e) == 'NEEDS_PASSWORD':
            return jsonify({
                'success': False,
                'needs_password': True,
                'error': '檔案已加密，請輸入密碼後再轉換'
            }), 200
        return jsonify({'success': False, 'error': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        current_app.logger.exception("Converter unexpected error")
        return jsonify({'success': False, 'error': f'伺服器錯誤：{e}'}), 500
    finally:
        # Always clean up the temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)


@converter_bp.route('/download/<path:filename>')
@login_required
def download(filename):
    """Serve a previously converted file for download."""
    # Security: strip any path traversal attempts
    filename = os.path.basename(filename)
    dl_dir   = _get_download_dir()
    file_path = os.path.join(dl_dir, filename)

    if not os.path.exists(file_path):
        flash('下載連結已過期，請重新轉換', 'danger')
        return redirect(url_for('converter.index'))

    # Derive friendly filename: strip leading token (32-char hex + underscore)
    parts = filename.split('_', 1)
    friendly = parts[1] if len(parts) == 2 and len(parts[0]) == 32 else filename

    return send_file(file_path, as_attachment=True, download_name=friendly)
