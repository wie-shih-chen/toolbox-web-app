"""
Flex Message Service
Builds LINE Flex Message JSON structures for rich card responses.
"""

WEB_BASE = "https://weishihchen.pythonanywhere.com"

CATEGORY_EMOJI = {
    "飲食": "🍔", "交通": "🚌", "娛樂": "🎮", "居住": "🏠", "其他": "📦",
}


class FlexMessageService:

    # ─────────────────────────────────────────────
    # CARD 1: Expense Confirm (green receipt)
    # ─────────────────────────────────────────────
    @staticmethod
    def build_expense_confirm(name, amount, category, timestamp, ai=False):
        label = "✨ AI 自動記帳" if ai else "✅ 支出記錄成功"
        cat_emoji = CATEGORY_EMOJI.get(category, "📦")
        return {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1a7a4a",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": label,
                        "color": "#FFFFFF",
                        "size": "md",
                        "weight": "bold"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"${amount:,}",
                        "size": "3xl",
                        "weight": "bold",
                        "color": "#1a7a4a",
                        "align": "center"
                    },
                    {"type": "separator"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "📌 名稱", "color": "#888888", "size": "sm", "flex": 2},
                            {"type": "text", "text": name, "color": "#111111", "size": "sm", "flex": 3, "align": "end", "wrap": True}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "🏷️ 類別", "color": "#888888", "size": "sm", "flex": 2},
                            {"type": "text", "text": f"{cat_emoji} {category}", "color": "#111111", "size": "sm", "flex": 3, "align": "end"}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "⏰ 時間", "color": "#888888", "size": "sm", "flex": 2},
                            {"type": "text", "text": str(timestamp)[5:16], "color": "#111111", "size": "sm", "flex": 3, "align": "end"}
                        ]
                    }
                ]
            }
        }

    # ─────────────────────────────────────────────
    # CARD 2: Expense Summary (dark monthly overview)
    # ─────────────────────────────────────────────
    @staticmethod
    def build_expense_summary(username, start_date, end_date, total, category_stats, records):
        month_label = f"{start_date[5:7]}月份記帳總覽"
        
        # Build category rows (top 5 by amount)
        cat_rows = []
        for cat_name, stats in sorted(category_stats.items(), key=lambda x: x[1]['amount'], reverse=True)[:5]:
            emoji = stats.get('emoji', '📦')
            cat_rows.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": f"{emoji} {cat_name}", "color": "#dddddd", "size": "sm", "flex": 3},
                    {"type": "text", "text": f"${stats['amount']:,}", "color": "#ffffff", "size": "sm", "flex": 2, "align": "end", "weight": "bold"},
                    {"type": "text", "text": f"{stats['count']}筆", "color": "#aaaaaa", "size": "sm", "flex": 1, "align": "end"}
                ]
            })

        # Build recent 5 records
        recent_rows = []
        for r in records[:5]:
            cat = r.get('category', '其他').split(' ')[0]
            recent_rows.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": str(r['timestamp'])[5:16], "color": "#aaaaaa", "size": "xs", "flex": 3},
                    {"type": "text", "text": cat, "color": "#dddddd", "size": "xs", "flex": 2},
                    {"type": "text", "text": f"${int(r['amount']):,}", "color": "#ffffff", "size": "xs", "flex": 2, "align": "end"}
                ]
            })

        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1c1c2e",
                "paddingAll": "20px",
                "contents": [
                    {"type": "text", "text": "📊 " + month_label, "color": "#FFFFFF", "size": "lg", "weight": "bold"},
                    {"type": "text", "text": username, "color": "#aaaaaa", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#242436",
                "paddingAll": "20px",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"${total:,}",
                        "size": "4xl",
                        "weight": "bold",
                        "color": "#7c6af7",
                        "align": "center"
                    },
                    {"type": "text", "text": f"{start_date} ～ {end_date}", "color": "#888888", "size": "xs", "align": "center"},
                    {"type": "separator", "color": "#444455", "margin": "md"},
                    {"type": "text", "text": "各類別統計", "color": "#aaaaaa", "size": "xs", "weight": "bold", "margin": "md"},
                    *cat_rows,
                    {"type": "separator", "color": "#444455", "margin": "md"},
                    {"type": "text", "text": "最近 5 筆", "color": "#aaaaaa", "size": "xs", "weight": "bold", "margin": "md"},
                    *recent_rows
                ] if records else [
                    {"type": "text", "text": f"${total:,}", "size": "4xl", "weight": "bold", "color": "#7c6af7", "align": "center"},
                    {"type": "text", "text": "此期間尚無記帳紀錄", "color": "#888888", "align": "center"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1c1c2e",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "查看完整記帳記錄 →",
                            "uri": f"{WEB_BASE}/expense"
                        },
                        "style": "primary",
                        "color": "#7c6af7",
                        "height": "sm"
                    }
                ]
            }
        }

    # ─────────────────────────────────────────────
    # CARD 3: Salary Confirm (blue)
    # ─────────────────────────────────────────────
    @staticmethod
    def build_salary_confirm(record_type, date, amount, hours=0, start_time=None, end_time=None, note=None, ai=False):
        is_shift = (record_type == 'shift')
        label = ("✨ AI 自動排班" if ai else "✅ 排班記錄成功") if is_shift else ("✨ AI 自動獎金" if ai else "✅ 獎金記錄成功")
        icon = "🕐" if is_shift else "🎁"
        
        rows = [
            {
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "📅 日期", "color": "#aaaacc", "size": "sm", "flex": 2},
                    {"type": "text", "text": date, "color": "#ffffff", "size": "sm", "flex": 3, "align": "end"}
                ]
            }
        ]
        if is_shift and start_time and end_time:
            rows.append({
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "⏱️ 時間", "color": "#aaaacc", "size": "sm", "flex": 2},
                    {"type": "text", "text": f"{start_time} ~ {end_time} ({hours:g}h)", "color": "#ffffff", "size": "sm", "flex": 3, "align": "end"}
                ]
            })
        if note:
            rows.append({
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "📝 備註", "color": "#aaaacc", "size": "sm", "flex": 2},
                    {"type": "text", "text": note, "color": "#ffffff", "size": "sm", "flex": 3, "align": "end", "wrap": True}
                ]
            })

        return {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1a3a6a",
                "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": label, "color": "#FFFFFF", "size": "md", "weight": "bold"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#1e2a45",
                "paddingAll": "16px",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{icon} ${amount:,.0f}",
                        "size": "3xl",
                        "weight": "bold",
                        "color": "#4dabf7",
                        "align": "center"
                    },
                    {"type": "separator", "color": "#334466"},
                    *rows
                ]
            }
        }

    # ─────────────────────────────────────────────
    # CARD 4: Salary Summary (dark blue monthly overview)
    # ─────────────────────────────────────────────
    @staticmethod
    def build_salary_summary(username, start_date, end_date, total_amt, total_hrs, type_stats, records):
        month_label = f"{start_date[5:7]}月份薪資總覽"

        stat_rows = []
        for rtype, stats in type_stats.items():
            line = f"${stats['amount']:,} ({stats['count']}筆"
            if stats.get('hours', 0) > 0:
                line += f", {stats['hours']:g}h"
            line += ")"
            stat_rows.append({
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "🕐 排班" if rtype == "排班" else "🎁 獎金", "color": "#ccddff", "size": "sm", "flex": 2},
                    {"type": "text", "text": line, "color": "#ffffff", "size": "sm", "flex": 4, "align": "end"}
                ]
            })

        recent_rows = []
        records_desc = sorted(records, key=lambda x: (x['date'], x.get('start_time', '')), reverse=True)
        for r in records_desc[:5]:
            rtype_label = "排班" if r['type'] == 'shift' else "獎金"
            detail = f"${r['amount']:,}"
            if r['type'] == 'shift':
                detail += f" ({r.get('hours', 0):g}h)"
            recent_rows.append({
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": r['date'][5:], "color": "#aaaacc", "size": "xs", "flex": 2},
                    {"type": "text", "text": rtype_label, "color": "#ccddff", "size": "xs", "flex": 2},
                    {"type": "text", "text": detail, "color": "#ffffff", "size": "xs", "flex": 3, "align": "end"}
                ]
            })

        body_contents = [
            {
                "type": "text",
                "text": f"${total_amt:,.0f}",
                "size": "4xl",
                "weight": "bold",
                "color": "#4dabf7",
                "align": "center"
            },
        ]
        if total_hrs > 0:
            body_contents.append({"type": "text", "text": f"共 {total_hrs:g} 小時", "color": "#888888", "size": "xs", "align": "center"})
        body_contents.append({"type": "text", "text": f"{start_date} ～ {end_date}", "color": "#666688", "size": "xs", "align": "center"})

        if records:
            body_contents += [
                {"type": "separator", "color": "#334466", "margin": "md"},
                {"type": "text", "text": "項目統計", "color": "#aaaacc", "size": "xs", "weight": "bold", "margin": "md"},
                *stat_rows,
                {"type": "separator", "color": "#334466", "margin": "md"},
                {"type": "text", "text": "最近 5 筆", "color": "#aaaacc", "size": "xs", "weight": "bold", "margin": "md"},
                *recent_rows
            ]
        else:
            body_contents.append({"type": "text", "text": "此期間尚無薪資紀錄", "color": "#888888", "align": "center"})

        return {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0d1b2a",
                "paddingAll": "20px",
                "contents": [
                    {"type": "text", "text": "💰 " + month_label, "color": "#FFFFFF", "size": "lg", "weight": "bold"},
                    {"type": "text", "text": username, "color": "#8899bb", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#131f30",
                "paddingAll": "20px",
                "spacing": "md",
                "contents": body_contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0d1b2a",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "查看詳細薪資記錄 →",
                            "uri": f"{WEB_BASE}/salary"
                        },
                        "style": "primary",
                        "color": "#4dabf7",
                        "height": "sm"
                    }
                ]
            }
        }
