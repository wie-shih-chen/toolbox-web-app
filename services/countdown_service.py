from app import db
from models import Countdown
import datetime

class CountdownService:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_all(self):
        """Get all countdowns and anniversaries, with calculated days."""
        items = Countdown.query.filter_by(user_id=self.user_id).order_by(
            Countdown.pinned.desc(), 
            Countdown.target_date.asc()
        ).all()
        return [self._format_item(item) for item in items]

    def get_pinned(self):
        """Get only pinned items for the dashboard."""
        items = Countdown.query.filter_by(user_id=self.user_id, pinned=True).order_by(
            Countdown.target_date.asc()
        ).all()
        return [self._format_item(item) for item in items]

    def _format_item(self, item):
        today = datetime.datetime.now().date()
        target = datetime.datetime.strptime(item.target_date, '%Y-%m-%d').date()
        days_diff = (target - today).days

        # For anniversary, it goes UP from target date (usually in past)
        # So days_passed = today - target = -days_diff
        
        # Determine status
        if item.is_anniversary:
            display_days = -days_diff
            if display_days < 0:
                is_past = False
                display_text = f"還有 {-display_days} 天開始"
            else:
                is_past = True
                display_text = f"已經 {display_days} 天"
        else:
            display_days = days_diff
            if display_days > 0:
                is_past = False
                display_text = f"還有 {display_days} 天"
            elif display_days == 0:
                is_past = False
                display_text = "就是今天！"
            else:
                is_past = True
                display_text = f"已過 {-display_days} 天"

        return {
            "id": item.id,
            "title": item.title,
            "target_date": item.target_date,
            "is_anniversary": item.is_anniversary,
            "icon": item.icon,
            "pinned": item.pinned,
            "days_diff": display_days,
            "is_past": is_past,
            "display_text": display_text
        }

    def add_event(self, data):
        new_item = Countdown(
            user_id=self.user_id,
            title=data.get('title'),
            target_date=data.get('target_date'),
            is_anniversary=data.get('is_anniversary', False),
            icon=data.get('icon', '📅'),
            pinned=data.get('pinned', False)
        )
        db.session.add(new_item)
        db.session.commit()
        return {"success": True, "id": new_item.id}

    def update_event(self, item_id, data):
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}
        
        item.title = data.get('title', item.title)
        item.target_date = data.get('target_date', item.target_date)
        if 'is_anniversary' in data:
            item.is_anniversary = data.get('is_anniversary')
        if 'icon' in data:
            item.icon = data.get('icon')
        if 'pinned' in data:
            item.pinned = data.get('pinned')

        db.session.commit()
        return {"success": True}

    def delete_event(self, item_id):
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}
        db.session.delete(item)
        db.session.commit()
        return {"success": True}

    def toggle_pin(self, item_id):
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}
        item.pinned = not item.pinned
        db.session.commit()
        return {"success": True, "pinned": item.pinned}
