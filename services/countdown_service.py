from models import db, Countdown, CountdownSubEvent
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
        """Get only pinned items for the dashboard, with next milestone data."""
        items = Countdown.query.filter_by(user_id=self.user_id, pinned=True).order_by(
            Countdown.target_date.asc()
        ).all()
        return [self._format_item(item, include_next_milestone=True) for item in items]

    def _format_item(self, item, include_next_milestone=False):
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
            
            # Auto-advance annual recurring countdowns
            if item.repeat_annually:
                try:
                    target_this_year = target.replace(year=today.year)
                except ValueError:
                    target_this_year = target.replace(year=today.year, day=28)
                
                if target_this_year < today:
                    try:
                        target = target.replace(year=today.year + 1)
                    except ValueError:
                        target = target.replace(year=today.year + 1, day=28)
                else:
                    target = target_this_year

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

        res = {
            "id": item.id,
            "title": item.title,
            "target_date": item.target_date,
            "is_anniversary": bool(item.is_anniversary),
            "icon": item.icon,
            "image_path": item.image_path,
            "pinned": bool(item.pinned),
            "notify_enabled": bool(item.notify_enabled),
            "days_diff": display_days,
            "is_past": is_past,
            "display_text": display_text,
            "repeat_annually": bool(item.repeat_annually)
        }

        if include_next_milestone:
            milestones = self.get_milestones(item.id)
            # Find first milestone that is in the future (today or later)
            next_m = next((m for m in milestones if m['days_from_today'] >= 0), None)
            if next_m:
                res["next_milestone"] = {
                    "title": next_m['title'],
                    "days_left": next_m['days_from_today'],
                    "date": next_m['target_date']
                }
            else:
                res["next_milestone"] = None

        return res

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
            pinned=data.get('pinned', False),
            notify_enabled=data.get('notify_enabled', True),
            repeat_annually=data.get('repeat_annually', False)
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
            item.pinned = bool(data.get('pinned'))
        if 'notify_enabled' in data:
            item.notify_enabled = bool(data.get('notify_enabled'))
        if 'repeat_annually' in data:
            item.repeat_annually = bool(data.get('repeat_annually'))
            
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

    def get_event(self, item_id):
        """Get a single countdown event by id."""
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return None
        return self._format_item(item)

    def get_milestones(self, item_id):
        """Return a sorted merged list of system milestones + custom sub-events for a countdown."""
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return []

        import datetime
        from dateutil.relativedelta import relativedelta

        tz_tw = datetime.timezone(datetime.timedelta(hours=8))
        today = datetime.datetime.now(tz_tw).date()
        target = datetime.datetime.strptime(item.target_date, '%Y-%m-%d').date()

        # --- System milestones (only for anniversary items) ---
        system = []
        if item.is_anniversary:
            # 50-day milestones up to 5 years out
            max_days = 365 * 5
            for n in range(50, max_days + 1, 50):
                milestone_date = target + datetime.timedelta(days=n - 1)  # inclusive
                label = f'{n}天'
                system.append({
                    'type': 'system',
                    'id': None,
                    'title': label,
                    'target_date': milestone_date.isoformat(),
                    'icon': '🗓️',
                    'days_from_today': (milestone_date - today).days,
                })
            # Annual milestones
            for y in range(1, 6):
                annual_date = target + relativedelta(years=y)
                label = f'{y}年'
                system.append({
                    'type': 'system',
                    'id': None,
                    'title': label,
                    'target_date': annual_date.isoformat(),
                    'icon': '🎉',
                    'days_from_today': (annual_date - today).days,
                })

        # --- Custom sub-events ---
        sub_events = CountdownSubEvent.query.filter_by(countdown_id=item_id).all()
        custom = []
        for se in sub_events:
            se_date = datetime.datetime.strptime(se.target_date, '%Y-%m-%d').date()
            if se.repeat_annually:
                # Expand to occurrences from 2 years ago to 5 years ahead
                base_month = se_date.month
                base_day = se_date.day
                for year_offset in range(-2, 6):
                    try:
                        occ_date = se_date.replace(year=today.year + year_offset)
                    except ValueError:
                        # Handle Feb 29 on non-leap years → use Feb 28
                        occ_date = se_date.replace(year=today.year + year_offset, day=28)
                    
                    # 跳過事件建立日之前的歷史重複年份
                    if occ_date < se_date:
                        continue
                        
                    custom.append({
                        'type': 'custom',
                        'id': se.id if occ_date == se_date else None,  # Only allow delete on the original
                        'title': se.title,
                        'target_date': occ_date.isoformat(),
                        'icon': se.icon,
                        'days_from_today': (occ_date - today).days,
                        'repeat_annually': True,
                        'sub_id': se.id,  # Always carry sub_id for delete
                    })
            else:
                custom.append({
                    'type': 'custom',
                    'id': se.id,
                    'title': se.title,
                    'target_date': se.target_date,
                    'icon': se.icon,
                    'days_from_today': (se_date - today).days,
                    'repeat_annually': False,
                    'sub_id': se.id,
                })

        # Merge, sort by date
        all_milestones = system + custom
        all_milestones.sort(key=lambda x: x['target_date'])
        return all_milestones

    def add_sub_event(self, item_id, data):
        """Add a custom sub-event/milestone to a countdown."""
        item = Countdown.query.filter_by(id=item_id, user_id=self.user_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        se = CountdownSubEvent(
            countdown_id=item_id,
            title=data.get('title', '新事件'),
            target_date=data.get('target_date'),
            icon=data.get('icon', '📅'),
            repeat_annually=data.get('repeat_annually', False),
        )
        db.session.add(se)
        db.session.commit()
        return {"success": True, "id": se.id}

    def update_sub_event(self, item_id, sub_id, data):
        """Update a custom sub-event."""
        se = CountdownSubEvent.query.filter_by(
            id=sub_id, countdown_id=item_id
        ).first()
        if not se:
            return {"success": False, "error": "Sub-event not found"}
            
        se.title = data.get('title', se.title)
        se.target_date = data.get('target_date', se.target_date)
        se.icon = data.get('icon', se.icon)
        if 'repeat_annually' in data:
            se.repeat_annually = bool(data.get('repeat_annually'))
            
        db.session.commit()
        return {"success": True}

    def delete_sub_event(self, item_id, sub_id):
        """Delete a custom sub-event."""
        se = CountdownSubEvent.query.filter_by(
            id=sub_id, countdown_id=item_id
        ).first()
        if not se:
            return {"success": False, "error": "Sub-event not found"}
        db.session.delete(se)
        db.session.commit()
        return {"success": True}
