import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Salary Data File (Absolute path to ensure it finds the existing file)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SALARY_DATA_FILE = os.path.join(BASE_DIR, 'salary_data.json')
    
    # Download Path (From existing app)
    DOWNLOAD_PATH = '/Users/weishichen/Documents/程式/python/youtube工具/下載的影音'
    
    # Ensure download directory exists
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
