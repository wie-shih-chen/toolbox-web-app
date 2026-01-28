from flask import Flask, render_template
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Register Blueprints
with app.app_context():
    from routes.main_routes import main_bp
    from routes.salary_routes import salary_bp
    from routes.download_routes import download_bp
    from routes.ntut_routes import ntut_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(salary_bp, url_prefix='/salary')
    app.register_blueprint(download_bp, url_prefix='/download')
    app.register_blueprint(ntut_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
