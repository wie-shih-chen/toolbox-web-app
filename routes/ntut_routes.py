from flask import Blueprint, render_template

ntut_bp = Blueprint('ntut', __name__, url_prefix='/ntut')

@ntut_bp.route('/calendar')
def calendar():
    return render_template('ntut/calendar.html')
