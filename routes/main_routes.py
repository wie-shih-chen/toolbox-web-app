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
    # Parse custom links
    custom_links_list = []
    if current_user.settings.custom_links:
        try:
            custom_links_list = json.loads(current_user.settings.custom_links)
        except:
            pass

    # Default full list of tools
    default_order = ['finance', 'salary', 'expense', 'downloader', 'countdown', 'reminder', 'calendar', 'period', 'shop', 'vocab']
    
    # Auto-append custom links to the end of dashboard_order if they are not already there
    custom_keys = [link['id'] for link in custom_links_list]
    for key in custom_keys:
        if key not in default_order:
            default_order.append(key)
    
    if not dashboard_order:
        dashboard_order = default_order
    else:
        # Auto-append any new tools or new custom links that the user doesn't have in their saved order yet
        for tool in default_order:
            if tool not in dashboard_order:
                dashboard_order.append(tool)
                
        # Also, remove any custom links from dashboard_order that were deleted by the user
        valid_keys = set(['finance', 'salary', 'expense', 'downloader', 'countdown', 'reminder', 'calendar', 'period', 'shop', 'vocab'] + custom_keys)
        dashboard_order = [key for key in dashboard_order if key in valid_keys]
        
    return render_template('index.html', pinned_countdowns=pinned_countdowns, dashboard_order=dashboard_order, custom_links=custom_links_list)
@main_bp.route('/manual')
@login_required
def manual():
    return render_template('manual.html')
