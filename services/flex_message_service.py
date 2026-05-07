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

    # ─────────────────────────────────────────────
    # CARD 5: Help Carousel (6 topic cards)
    # ─────────────────────────────────────────────
    @staticmethod
    def build_help_carousel():
        def _card(bg_header, emoji, title, subtitle, rows, tip=None):
            body_items = []
            for row in rows:
                body_items.append({
                    "type": "box", "layout": "horizontal", "spacing": "sm",
                    "contents": [
                        {"type": "text", "text": row[0], "color": "#aaaaaa", "size": "xs", "flex": 3, "wrap": True},
                        {"type": "text", "text": row[1], "color": "#ffffff", "size": "xs", "flex": 4, "wrap": True, "align": "end"}
                    ]
                })
            if tip:
                body_items += [
                    {"type": "separator", "color": "#333355", "margin": "md"},
                    {"type": "text", "text": tip, "color": "#aaaaaa", "size": "xxs", "wrap": True, "margin": "sm"}
                ]
            return {
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box", "layout": "vertical",
                    "backgroundColor": bg_header, "paddingAll": "14px",
                    "contents": [
                        {"type": "text", "text": f"{emoji} {title}", "color": "#FFFFFF", "size": "md", "weight": "bold"},
                        {"type": "text", "text": subtitle, "color": "#ccccff", "size": "xs", "margin": "xs"}
                    ]
                },
                "body": {
                    "type": "box", "layout": "vertical",
                    "backgroundColor": "#1a1a2e", "paddingAll": "14px", "spacing": "sm",
                    "contents": body_items
                }
            }

        card_ai = {
            "type": "bubble", "size": "kilo",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#2d1b69", "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": "🤖 AI 智慧助手", "color": "#FFFFFF", "size": "md", "weight": "bold"},
                    {"type": "text", "text": "直接說話就能記錄！", "color": "#bb99ff", "size": "xs", "margin": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1a1a2e", "paddingAll": "14px", "spacing": "sm",
                "contents": [
                    {"type": "text", "text": "不需要記格式，直接用口語說：", "color": "#cccccc", "size": "xs", "wrap": True},
                    {"type": "separator", "color": "#333355"},
                    {"type": "text", "text": "「昨天買珍奶花了65」", "color": "#bb99ff", "size": "sm", "wrap": True},
                    {"type": "text", "text": "「今天下午2到6點打工」", "color": "#bb99ff", "size": "sm", "wrap": True},
                    {"type": "text", "text": "「老闆發了1500獎金」", "color": "#bb99ff", "size": "sm", "wrap": True},
                    {"type": "text", "text": "「大姨媽來了肚子有點痛」", "color": "#bb99ff", "size": "sm", "wrap": True},
                    {"type": "separator", "color": "#333355"},
                    {"type": "text", "text": "AI 會自動幫你歸類並記錄，也聽得懂「昨天」「上週五」等時間詞！", "color": "#888888", "size": "xxs", "wrap": True}
                ]
            }
        }

        card_expense = _card(
            "#1a4a2e", "📝", "記帳", "記錄每一筆支出",
            [
                ("指令格式", "記帳 [名稱] [類別] [金額]"),
                ("類別選項", "飲食/交通/娛樂/居住/其他"),
                ("範例 1", "記帳 午餐 150"),
                ("範例 2", "記帳 便當 飲食 80 4/18"),
                ("查詢指令", "查詢記帳 [月份(可省)]"),
            ],
            tip="💡 類別和日期可省略，金額一定要有數字"
        )

        card_shift = _card(
            "#1a3a6a", "⏰", "排班", "記錄打工上班時段",
            [
                ("指令格式", "排班 [開始時間] [結束時間]"),
                ("範例 1", "排班 1300 1800"),
                ("範例 2", "排班 4/18 1200 1800"),
                ("查詢指令", "查詢薪水 [月份(可省)]"),
            ],
            tip="💡 時間可用 1300 或 13:00 格式"
        )

        card_bonus = _card(
            "#4a3a1a", "💰", "獎金", "記錄額外薪資收入",
            [
                ("指令格式", "獎金 [金額] [備註(可省)]"),
                ("範例 1", "獎金 1500"),
                ("範例 2", "獎金 2000 4/18 端午禮金"),
                ("查詢指令", "查詢薪水"),
            ],
            tip="💡 日期和備註可省略"
        )

        card_period = _card(
            "#4a1a2e", "🩸", "生理期", "記錄月經週期",
            [
                ("指令格式", "月經 [開始日(可省)] [結束日(可省)]"),
                ("開始記錄", "月經"),
                ("指定日期", "月經 4/18 4/22"),
                ("結束紀錄", "月經 結束"),
            ],
            tip="💡 直接輸入「月經」會以今天為開始日"
        )

        card_query = _card(
            "#2a2a2a", "🔍", "查詢", "查看本月統計報告",
            [
                ("記帳總覽", "查詢記帳"),
                ("指定月份", "查詢記帳 4月"),
                ("薪資總覽", "查詢薪水"),
                ("指定月份", "查詢薪水 4月"),
            ],
            tip="💡 不指定月份預設查詢本月"
        )

        return {
            "type": "carousel",
            "contents": [card_ai, card_expense, card_shift, card_bonus, card_period, card_query]
        }
