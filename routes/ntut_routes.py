from flask import Blueprint, render_template
from flask_login import login_required

ntut_bp = Blueprint('ntut', __name__, url_prefix='/ntut')

@ntut_bp.route('/calendar')
@login_required
def calendar():
    return render_template('ntut/calendar.html')
