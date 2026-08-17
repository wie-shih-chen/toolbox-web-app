from flask import Blueprint, render_template
from flask_login import login_required, current_user
from services.countdown_service import CountdownService

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    cd_service = CountdownService(current_user.id)
    pinned_countdowns = cd_service.get_pinned()
    import json
    dashboard_order = []
    if current_user.settings.dashboard_order:
        try:
            dashboard_order = json.loads(current_user.settings.dashboard_order)
        except:
            pass
            
    # Default full list of tools
    default_order = ['finance', 'salary', 'expense', 'downloader', 'countdown', 'reminder', 'calendar', 'period', 'shop', 'vocab', 'group']
    
    if not dashboard_order:
        dashboard_order = default_order
    else:
        # Auto-append any new tools that the user doesn't have in their saved order yet
        for tool in default_order:
            if tool not in dashboard_order:
                dashboard_order.append(tool)
        
    return render_template('index.html', pinned_countdowns=pinned_countdowns, dashboard_order=dashboard_order)
@main_bp.route('/manual')
@login_required
def manual():
    return render_template('manual.html')
