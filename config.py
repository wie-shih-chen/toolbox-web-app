import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # SSO (Single Sign-On) Config
    # 在 PythonAnywhere 環境變數設定相同的值（兩個 app 共用）
    SSO_SECRET  = os.environ.get('SSO_SECRET', '213babe7434b974ea9f295eadc2788a377ce87de9d964d8d71ed55f520299e1e')
    WEB2_URL    = os.environ.get('WEB2_URL', 'https://weishihchensec.pythonanywhere.com')
    # Salary Data File
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SALARY_DATA_FILE = os.path.join(BASE_DIR, 'salary_data.json')
    
    # Add project bin to PATH (for ffmpeg on Render)
    BIN_DIR = os.path.join(BASE_DIR, 'bin')
    if os.path.exists(BIN_DIR):
        os.environ['PATH'] = BIN_DIR + os.pathsep + os.environ['PATH']
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Download Path (relative to project root)
    DOWNLOAD_PATH = os.path.join(BASE_DIR, 'downloads')
    
    # Ensure download directory exists
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
