import os
import subprocess
import tempfile
import shutil
import uuid

# Optional: pikepdf for PDF password removal
try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

# Optional: Pillow for image operations
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


class ConverterService:
    """
    File conversion service optimised for PythonAnywhere free tier.
    Uses LibreOffice (soffice) and Ghostscript (gs) which are pre-installed.
    """

    # Maximum upload size: 32 MB
    MAX_FILE_SIZE = 32 * 1024 * 1024

    # Allowed MIME / extension groups
    DOCUMENT_INPUT_EXTS = {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt', '.odp', '.ods', '.rtf', '.txt', '.csv', '.html', '.htm'}
    IMAGE_INPUT_EXTS    = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    PDF_EXT             = {'.pdf'}

    ALL_ALLOWED_EXTS = DOCUMENT_INPUT_EXTS | IMAGE_INPUT_EXTS | PDF_EXT

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tmp_dir():
        """Return a fresh temporary directory path (caller must clean up)."""
        return tempfile.mkdtemp(prefix='corex_conv_')

    @staticmethod
    def _safe_filename(original: str) -> str:
        """Build a unique safe filename preserving the original extension."""
        base, ext = os.path.splitext(original)
        return f"{uuid.uuid4().hex}{ext.lower()}"

    @staticmethod
    def _ext(path: str) -> str:
        return os.path.splitext(path)[1].lower()

    # ------------------------------------------------------------------ #
    # LibreOffice conversion
    # ------------------------------------------------------------------ #

    @staticmethod
    def _libreoffice_convert(src_path: str, out_format: str, out_dir: str) -> str:
        """
        Run LibreOffice headless conversion.
        out_format examples: 'pdf', 'docx', 'pptx', 'xlsx', 'png'
        Returns the path of the output file.
        """
        # PythonAnywhere has 'soffice' in PATH; fallback to common locations
        soffice = shutil.which('soffice') or shutil.which('libreoffice') or '/usr/bin/soffice'

        cmd = [
            soffice,
            '--headless',
            '--norestore',
            '--nofirststartwizard',
            '--convert-to', out_format,
            '--outdir', out_dir,
            src_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice error: {result.stderr.strip() or result.stdout.strip()}")

        # LibreOffice names the output: <basename>.<out_format>
        # The format string can be e.g. "docx:writer8" so we split on ':'
        fmt_ext = out_format.split(':')[0]
        base = os.path.splitext(os.path.basename(src_path))[0]
        out_path = os.path.join(out_dir, f"{base}.{fmt_ext}")
        if not os.path.exists(out_path):
            # Search for any newly created file in out_dir
            files = os.listdir(out_dir)
            candidates = [f for f in files if f.startswith(base)]
            if candidates:
                out_path = os.path.join(out_dir, candidates[0])
            else:
                raise RuntimeError("LibreOffice did not produce an output file.")
        return out_path

    # ------------------------------------------------------------------ #
    # Public: Document conversion
    # ------------------------------------------------------------------ #

    # Which LibreOffice application handles which extension
    WRITER_EXTS  = {'.doc', '.docx', '.odt', '.rtf', '.txt', '.html', '.htm'}
    IMPRESS_EXTS = {'.ppt', '.pptx', '.odp'}
    CALC_EXTS    = {'.xls', '.xlsx', '.ods', '.csv'}

    # Valid (src_type → target_fmt) combinations
    _ALLOWED_CONVERSIONS = {
        'writer':  {'pdf', 'docx', 'doc', 'odt', 'txt', 'html', 'png'},
        'impress': {'pdf', 'pptx', 'ppt', 'odp', 'png'},
        'calc':    {'pdf', 'xlsx', 'xls', 'ods', 'csv', 'html'},
        'pdf':     {'docx', 'pptx', 'png'},   # best-effort
        'image':   {'pdf'},
    }

    # Explicit LibreOffice filter strings (improves accuracy)
    _LO_FILTERS = {
        'pdf':  'pdf:writer_pdf_Export',
        'docx': 'docx:MS Word 2007 XML',
        'doc':  'doc:MS Word 97',
        'odt':  'odt:writer8',
        'txt':  'txt:Text',
        'html': 'html:HTML (StarWriter)',
        'pptx': 'pptx:Impress MS PowerPoint 2007 XML',
        'ppt':  'ppt:MS PowerPoint 97',
        'odp':  'odp:impress8',
        'xlsx': 'xlsx:Calc MS Excel 2007 XML',
        'xls':  'xls:MS Excel 97',
        'ods':  'ods:calc8',
        'csv':  'csv:Text - txt - csv (StarCalc)',
        'png':  'png:draw_png_Export',
    }

    @staticmethod
    def _src_type(ext: str) -> str:
        """Return the LibreOffice application type for a given source extension."""
        e = ext.lower()
        if e in ConverterService.WRITER_EXTS:  return 'writer'
        if e in ConverterService.IMPRESS_EXTS: return 'impress'
        if e in ConverterService.CALC_EXTS:    return 'calc'
        if e == '.pdf':                         return 'pdf'
        if e in ConverterService.IMAGE_INPUT_EXTS: return 'image'
        return 'unknown'

    @staticmethod
    def validate_conversion(src_ext: str, target_fmt: str) -> None:
        """
        Raise ValueError if the conversion is not supported.
        This prevents impossible conversions (e.g. docx → pptx).
        """
        src_type = ConverterService._src_type(src_ext)
        allowed  = ConverterService._ALLOWED_CONVERSIONS.get(src_type, set())
        if target_fmt not in allowed:
            src_label = {
                'writer':  'Word/文字文件',
                'impress': 'PowerPoint/簡報',
                'calc':    'Excel/試算表',
                'pdf':     'PDF',
                'image':   '圖片',
            }.get(src_type, src_ext)
            raise ValueError(
                f'不支援此轉換：{src_label} → .{target_fmt.upper()}。'
                f'支援的輸出格式：{", ".join(sorted(allowed)) or "無"}')


    @staticmethod
    def pdf_to_docx(src_path: str, out_dir: str) -> str:
        """Convert PDF → DOCX via LibreOffice (best-effort, layout may vary)."""
        return ConverterService._libreoffice_convert(src_path, 'docx:MS Word 2007 XML', out_dir)

    @staticmethod
    def doc_to_format(src_path: str, target_fmt: str, out_dir: str) -> str:
        """Generic document conversion with validation + explicit LibreOffice filters."""
        src_ext = ConverterService._ext(src_path)
        # Validate: raises ValueError for unsupported combos (e.g. docx→pptx)
        ConverterService.validate_conversion(src_ext, target_fmt)
        lo_fmt = ConverterService._LO_FILTERS.get(target_fmt, target_fmt)
        return ConverterService._libreoffice_convert(src_path, lo_fmt, out_dir)

    # ------------------------------------------------------------------ #
    # Public: PDF utilities
    # ------------------------------------------------------------------ #

    @staticmethod
    def pdf_unlock(src_path: str, password: str, out_dir: str) -> str:
        """
        Remove password protection from a PDF.
        Uses pikepdf (preferred) or Ghostscript as fallback.
        """
        base = os.path.splitext(os.path.basename(src_path))[0]
        out_path = os.path.join(out_dir, f"{base}_unlocked.pdf")

        if HAS_PIKEPDF:
            try:
                with pikepdf.open(src_path, password=password) as pdf:
                    pdf.save(out_path)
                return out_path
            except pikepdf.PasswordError:
                raise ValueError("密碼錯誤，請重新確認 PDF 密碼。")
            except Exception as e:
                raise RuntimeError(f"pikepdf 解鎖失敗：{e}")

        # Fallback: Ghostscript
        gs = shutil.which('gs') or shutil.which('ghostscript') or '/usr/bin/gs'
        cmd = [
            gs,
            '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=pdfwrite',
            '-dNOPAUSEREADINPUTFILE',
            f'-sPDFPassword={password}',
            f'-sOutputFile={out_path}',
            src_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if 'Password' in stderr or 'password' in stderr:
                raise ValueError("密碼錯誤，請重新確認 PDF 密碼。")
            raise RuntimeError(f"Ghostscript 解鎖失敗：{stderr}")
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError("解鎖後的 PDF 產生失敗，請確認密碼是否正確。")
        return out_path

    @staticmethod
    def pdf_compress(src_path: str, quality: str, out_dir: str) -> str:
        """
        Compress a PDF using Ghostscript.
        quality: 'screen' | 'ebook' | 'printer' | 'prepress'
        """
        quality_map = {
            'low':    'screen',
            'medium': 'ebook',
            'high':   'printer',
        }
        gs_quality = quality_map.get(quality, 'ebook')
        base = os.path.splitext(os.path.basename(src_path))[0]
        out_path = os.path.join(out_dir, f"{base}_compressed.pdf")

        gs = shutil.which('gs') or '/usr/bin/gs'
        cmd = [
            gs,
            '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER',
            '-sDEVICE=pdfwrite',
            f'-dPDFSETTINGS=/{gs_quality}',
            '-dCompatibilityLevel=1.4',
            f'-sOutputFile={out_path}',
            src_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Ghostscript 壓縮失敗：{result.stderr.strip()}")
        return out_path

    @staticmethod
    def image_to_pdf(src_path: str, out_dir: str) -> str:
        """Convert an image → PDF via LibreOffice or Pillow."""
        base = os.path.splitext(os.path.basename(src_path))[0]
        out_path = os.path.join(out_dir, f"{base}.pdf")

        if HAS_PILLOW:
            img = Image.open(src_path).convert('RGB')
            img.save(out_path, 'PDF', resolution=100.0)
            return out_path

        # Fallback: LibreOffice
        return ConverterService._libreoffice_convert(src_path, 'pdf', out_dir)

    @staticmethod
    def pdf_to_images(src_path: str, out_dir: str, fmt: str = 'png', dpi: int = 150) -> list:
        """
        Convert PDF pages → images using Ghostscript.
        Returns list of output file paths.
        """
        base = os.path.splitext(os.path.basename(src_path))[0]
        out_pattern = os.path.join(out_dir, f"{base}_%03d.{fmt}")

        device_map = {'png': 'png16m', 'jpg': 'jpeg', 'jpeg': 'jpeg'}
        device = device_map.get(fmt, 'png16m')

        gs = shutil.which('gs') or '/usr/bin/gs'
        cmd = [
            gs,
            '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER',
            f'-sDEVICE={device}',
            f'-r{dpi}',
            f'-sOutputFile={out_pattern}',
            src_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"PDF→圖片失敗：{result.stderr.strip()}")

        files = sorted([
            os.path.join(out_dir, f)
            for f in os.listdir(out_dir)
            if f.startswith(base) and f.endswith(f'.{fmt}')
        ])
        return files

    # ------------------------------------------------------------------ #
    # Public: Image conversion / compression
    # ------------------------------------------------------------------ #

    @staticmethod
    def convert_image(src_path: str, target_fmt: str, out_dir: str,
                      quality: int = 85, max_width: int = None) -> str:
        """
        Convert / compress an image using Pillow.
        target_fmt: 'jpg', 'png', 'webp', etc.
        """
        if not HAS_PILLOW:
            raise RuntimeError("Pillow 未安裝，無法進行圖片轉換。")

        base = os.path.splitext(os.path.basename(src_path))[0]
        fmt_upper = target_fmt.upper().replace('JPG', 'JPEG')
        out_ext   = 'jpg' if target_fmt == 'jpeg' else target_fmt
        out_path  = os.path.join(out_dir, f"{base}.{out_ext}")

        img = Image.open(src_path)
        if img.mode in ('RGBA', 'P') and fmt_upper == 'JPEG':
            img = img.convert('RGB')
        if max_width and img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        save_kwargs = {}
        if fmt_upper in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
        img.save(out_path, fmt_upper, **save_kwargs)
        return out_path

    # ------------------------------------------------------------------ #
    # Utility: human-readable file size
    # ------------------------------------------------------------------ #

    @staticmethod
    def human_size(n_bytes: int) -> str:
        for unit in ('B', 'KB', 'MB', 'GB'):
            if n_bytes < 1024:
                return f"{n_bytes:.1f} {unit}"
            n_bytes /= 1024
        return f"{n_bytes:.1f} TB"
