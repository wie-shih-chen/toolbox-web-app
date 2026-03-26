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
        import datetime
        # Enforce UTC+8 (Taiwan Time)
        tz_tw = datetime.timezone(datetime.timedelta(hours=8))
        today = datetime.datetime.now(tz_tw).date()
        target = datetime.datetime.strptime(item.target_date, '%Y-%m-%d').date()

        from dateutil.relativedelta import relativedelta
        
        # Determine status
        if item.is_anniversary:
            # Anniversary: includes the start day (today - target + 1)
            days_diff = (today - target).days + 1
            if days_diff < 0:
                is_past = False
                display_text = f"還有 {-days_diff + 1} 天開始" # Not yet started
                display_days = -days_diff + 1
            else:
                is_past = True
                
                # Use relativedelta for precise months and days
                rd = relativedelta(today + datetime.timedelta(days=1), target)
                
                parts = []
                if rd.years > 0:
                    parts.append(f"{rd.years}年")
                if rd.months > 0:
                    parts.append(f"{rd.months}個月")
                if rd.days > 0 or (rd.years == 0 and rd.months == 0):
                    parts.append(f"{rd.days}天")
                
                display_text = " ".join(parts)
                display_days = days_diff
        else:
            # Countdown: excludes the start day (target - today)
            days_diff = (target - today).days
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
                display_days = -display_days

        return {
            "id": item.id,
            "title": item.title,
            "target_date": item.target_date,
            "is_anniversary": item.is_anniversary,
            "icon": item.icon,
            "image_path": item.image_path,
            "pinned": item.pinned,
            "days_diff": display_days,
            "is_past": is_past,
            "display_text": display_text
        }

    def _save_base64_image(self, image_data):
        import base64
        import uuid
        import os
        from flask import current_app

        if not image_data or not image_data.startswith('data:image'):
            return None

        try:
            # Format: 'data:image/jpeg;base64,...'
            header, encoded = image_data.split(",", 1)
            file_ext = header.split(';')[0].split('/')[1]
            
            # Map standard JS extensions
            if file_ext == 'jpeg': file_ext = 'jpg'
            
            filename = f"cd_{uuid.uuid4().hex}.{file_ext}"
            filepath = os.path.join(current_app.root_path, 'static', 'uploads', 'countdowns', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, "wb") as fh:
                fh.write(base64.b64decode(encoded))
                
            return f"uploads/countdowns/{filename}"
        except Exception as e:
            print(f"Error saving image: {e}")
            return None

    def add_event(self, data):
        image_path = None
        if data.get('image_data'):
            image_path = self._save_base64_image(data.get('image_data'))

        new_item = Countdown(
            user_id=self.user_id,
            title=data.get('title'),
            target_date=data.get('target_date'),
            is_anniversary=data.get('is_anniversary', False),
            icon=data.get('icon', '📅'),
            image_path=image_path,
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
            
        if data.get('image_data'):
            import os
            from flask import current_app
            new_path = self._save_base64_image(data.get('image_data'))
            if new_path:
                # remove old image if exists
                if item.image_path:
                    old_path = os.path.join(current_app.root_path, 'static', item.image_path)
                    try:
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except:
                        pass
                item.image_path = new_path
        elif data.get('clear_image'):
            import os
            from flask import current_app
            if item.image_path:
                old_path = os.path.join(current_app.root_path, 'static', item.image_path)
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except:
                    pass
            item.image_path = None

        db.session.commit()
        return {"success": True}

    def delete_event(self, item_id):
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}
            
        import os
        from flask import current_app
        if item.image_path:
            old_path = os.path.join(current_app.root_path, 'static', item.image_path)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except:
                pass
                
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
