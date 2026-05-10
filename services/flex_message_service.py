"""
Flex Message Service
=====================
負責組合 LINE Flex Message JSON 模板。
"""

import os
from datetime import datetime

# 基礎 URL，用於按鈕連結
WEB_BASE = os.environ.get('WEB_BASE', 'https://line.me')

class FlexMessageService:

    @staticmethod
    def build_help_carousel():
        """建立功能說明的輪播卡片"""
        bubbles = [
            # 記帳功能
            {
                "type": "bubble", "size": "kilo",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#03a9f4", "contents": [{"type": "text", "text": "💰 記帳功能", "color": "#ffffff", "weight": "bold", "size": "sm"}]},
                "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                    {"type": "text", "text": "快速記錄每一筆花費", "weight": "bold", "size": "md", "wrap": True},
                    {"type": "text", "text": "👉 「記帳 午餐 150」", "size": "sm", "color": "#666666"},
                    {"type": "text", "text": "👉 「語音/文字：昨天喝了杯 60 元咖啡」", "size": "sm", "color": "#666666"},
                    {"type": "text", "text": "👉 「查詢本月記帳」", "size": "sm", "color": "#666666"}
                ]}
            },
            # 薪資功能
            {
                "type": "bubble", "size": "kilo",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#4caf50", "contents": [{"type": "text", "text": "🕒 薪資管理", "color": "#ffffff", "weight": "bold", "size": "sm"}]},
                "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                    {"type": "text", "text": "記錄排班與獎金", "weight": "bold", "size": "md", "wrap": True},
                    {"type": "text", "text": "👉 「排班 1400 1900」", "size": "sm", "color": "#666666"},
                    {"type": "text", "text": "👉 「獎金 1500 三節」", "size": "sm", "color": "#666666"},
                    {"type": "text", "text": "👉 「2到5月的薪資」", "size": "sm", "color": "#666666"}
                ]}
            },
            # 生理期功能
            {
                "type": "bubble", "size": "kilo",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#f06292", "contents": [{"type": "text", "text": "🩸 生理期助手", "color": "#ffffff", "weight": "bold", "size": "sm"}]},
                "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                    {"type": "text", "text": "預測與記錄生理期", "weight": "bold", "size": "md", "wrap": True},
                    {"type": "text", "text": "👉 「月經來了」 / 「月經結束」", "size": "sm", "color": "#666666"},
                    {"type": "text", "text": "👉 「下次月經什麼時候？」", "size": "sm", "color": "#666666"}
                ]}
            }
        ]
        return {"type": "carousel", "contents": bubbles}

    @staticmethod
    def build_trend_bubble(title, labels, values, color="#03a9f4", unit="元"):
        """使用 QuickChart API 建立趨勢圖卡片"""
        # 建構 QuickChart URL
        import urllib.parse
        chart_config = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": title,
                    "data": values,
                    "fill": True,
                    "backgroundColor": "rgba(3, 169, 244, 0.1)",
                    "borderColor": color,
                    "pointBackgroundColor": color,
                    "borderWidth": 3,
                    "lineTension": 0.4
                }]
            },
            "options": {
                "legend": {"display": False},
                "scales": {
                    "yAxes": [{"ticks": {"beginAtZero": True, "fontColor": "#8b949e"}}],
                    "xAxes": [{"ticks": {"fontColor": "#8b949e"}}]
                }
            }
        }
        
        config_str = str(chart_config).replace("True", "true").replace("False", "false")
        encoded_config = urllib.parse.quote(config_str)
        chart_url = f"https://quickchart.io/chart?bkg=transparent&c={encoded_config}&w=500&h=300"

        return {
            "type": "bubble", "size": "mega",
            "styles": {"body": {"backgroundColor": "#121d2b"}},
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": f"📈 {title}趨勢分析", "weight": "bold", "color": "#ffffff", "size": "xl"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "contents": [
                        {"type": "image", "url": chart_url, "size": "full", "aspectRatio": "1.6:1", "aspectMode": "fit"}
                    ]},
                    {"type": "separator", "margin": "xl", "color": "#2c3e50"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [
                        {"type": "text", "text": "數據總覽", "color": "#8b949e", "size": "xs", "weight": "bold"}
                    ] + [
                        {
                            "type": "box", "layout": "horizontal", "contents": [
                                {"type": "text", "text": label, "size": "xs", "color": "#ffffff"},
                                {"type": "text", "text": f"${val:,.0f}{unit}", "size": "xs", "color": "#ffffff", "align": "end"}
                            ]
                        } for label, val in zip(labels, values)
                    ]}
                ]
            }
        }

    @staticmethod
    def build_expense_confirm(name, amount, category, timestamp, ai=False):
        """建立記帳成功的確認卡片"""
        return {
            "type": "bubble", "size": "kilo",
            "body": {
                "type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "✅ 記帳成功" if not ai else "🤖 AI 記帳成功", "weight": "bold", "color": "#1DB446", "size": "sm"},
                    {"type": "text", "text": name, "weight": "bold", "size": "xl", "margin": "md"},
                    {"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "金額", "color": "#aaaaaa", "size": "sm", "flex": 2},
                            {"type": "text", "text": f"${amount:,.0f}", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                        ]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "類別", "color": "#aaaaaa", "size": "sm", "flex": 2},
                            {"type": "text", "text": category, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                        ]},
                        {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                            {"type": "text", "text": "時間", "color": "#aaaaaa", "size": "sm", "flex": 2},
                            {"type": "text", "text": timestamp, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                        ]}
                    ]}
                ]
            }
        }

    @staticmethod
    def build_salary_confirm(record_type, date, amount, hours=0, start_time=None, end_time=None, note=None, ai=False):
        """建立薪資紀錄成功的確認卡片"""
        title = "打工排班" if record_type == 'shift' else "獎金/其他"
        color = "#03a9f4" if record_type == 'shift' else "#4caf50"
        
        contents = [
            {"type": "text", "text": f"✅ {title}紀錄成功" if not ai else f"🤖 AI {title}紀錄", "weight": "bold", "color": color, "size": "sm"},
            {"type": "text", "text": f"${amount:,.0f}", "weight": "bold", "size": "xl", "margin": "md"}
        ]
        
        info_rows = [
            {"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                {"type": "text", "text": "日期", "color": "#aaaaaa", "size": "sm", "flex": 2},
                {"type": "text", "text": date, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
            ]}
        ]
        
        if record_type == 'shift':
            info_rows.append({"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                {"type": "text", "text": "時間", "color": "#aaaaaa", "size": "sm", "flex": 2},
                {"type": "text", "text": f"{start_time} - {end_time} ({hours:g}h)", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
            ]})
        
        if note:
            info_rows.append({"type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                {"type": "text", "text": "備註", "color": "#aaaaaa", "size": "sm", "flex": 2},
                {"type": "text", "text": note, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
            ]})
            
        contents.append({"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": info_rows})
        
        return {"type": "bubble", "size": "kilo", "body": {"type": "box", "layout": "vertical", "contents": contents}}

    @staticmethod
    def build_expense_summary_bubble(username, start_date, end_date, total, category_stats, records):
        """建立單個月份的記帳總覽 Bubble (用於 Carousel)"""
        month_label = f"{int(start_date[5:7]):02d}月份"
        
        category_rows = []
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1]['amount'], reverse=True)
        for cat_name, stats in sorted_cats:
            category_rows.append({
                "type": "box", "layout": "horizontal", "margin": "md",
                "contents": [
                    {"type": "text", "text": f"{stats['emoji']} {cat_name}", "size": "sm", "color": "#ffffff", "flex": 3},
                    {"type": "text", "text": f"${stats['amount']:,} ({stats['count']}筆)", "size": "sm", "color": "#ffffff", "align": "end", "flex": 7}
                ]
            })

        record_rows = []
        for r in records:
            day = r['timestamp'][8:10]
            record_rows.append({
                "type": "box", "layout": "horizontal", "margin": "sm",
                "contents": [
                    {"type": "text", "text": f"{day}日", "size": "xs", "color": "#aaaaaa", "flex": 2},
                    {"type": "text", "text": r['note'], "size": "xs", "color": "#ffffff", "flex": 5, "maxLines": 1},
                    {"type": "text", "text": f"${int(r['amount']):,}", "size": "xs", "color": "#ffffff", "align": "end", "flex": 3}
                ]
            })

        return {
            "type": "bubble", "size": "mega",
            "styles": {"body": {"backgroundColor": "#121d2b"}},
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": f"💰 {month_label}記帳總覽", "weight": "bold", "color": "#ffffff", "size": "xl"},
                    {"type": "text", "text": username, "color": "#8b949e", "size": "sm", "margin": "xs"},
                    {"type": "box", "layout": "vertical", "margin": "xxl", "spacing": "sm", "contents": [
                        {"type": "text", "text": f"${total:,.0f}", "size": "4xl", "color": "#03a9f4", "weight": "bold", "align": "center"},
                        {"type": "text", "text": f"{start_date} ~ {end_date}", "size": "xs", "color": "#8b949e", "align": "center"}
                    ]},
                    {"type": "separator", "margin": "xl", "color": "#2c3e50"},
                    {"type": "text", "text": "分類統計", "weight": "bold", "color": "#8b949e", "size": "sm", "margin": "lg"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": category_rows or [{"type":"text","text":"暫無資料","color":"#555555"}]},
                    {"type": "separator", "margin": "xl", "color": "#2c3e50"},
                    {"type": "text", "text": "最近 10 筆", "weight": "bold", "color": "#8b949e", "size": "sm", "margin": "lg"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": record_rows or [{"type":"text","text":"暫無資料","color":"#555555"}]},
                    {"type": "box", "layout": "vertical", "margin": "xl", "contents": [
                        {"type": "button", "action": {"type": "uri", "label": "查看全部記錄 →", "uri": f"{WEB_BASE}/expense/"}, "style": "primary", "color": "#03a9f4", "height": "sm"}
                    ]}
                ]
            }
        }

    @staticmethod
    def build_expense_summary(username, start_date, end_date, total, category_stats, records):
        bubble = FlexMessageService.build_expense_summary_bubble(username, start_date, end_date, total, category_stats, records[:5])
        return {"type": "flex", "altText": f"{start_date[5:7]}月份記帳總覽", "contents": bubble}

    @staticmethod
    def build_salary_summary_bubble(username, start_date, end_date, total_amt, total_hrs, type_stats, records):
        """建立單個月份的薪資總覽 Bubble (用於 Carousel)"""
        month_label = f"{int(start_date[5:7]):02d}月份"
        
        stat_rows = []
        for rtype, stats in type_stats.items():
            info = f"${stats['amount']:,} ({stats['count']}筆)"
            if stats['hours'] > 0:
                info = f"${stats['amount']:,} ({stats['count']}筆, {stats['hours']:g}h)"
            stat_rows.append({
                "type": "box", "layout": "horizontal", "margin": "md",
                "contents": [
                    {"type": "text", "text": "🕒 排班" if rtype == "排班" else "💰 獎金", "size": "sm", "color": "#ffffff", "flex": 3},
                    {"type": "text", "text": info, "size": "sm", "color": "#ffffff", "align": "end", "flex": 7}
                ]
            })

        record_rows = []
        for r in records:
            date_label = r['date'][5:]
            info = f"${int(r['amount']):,}"
            if r['type'] == 'shift':
                info = f"${int(r['amount']):,} ({r['hours']:g}h)"
            record_rows.append({
                "type": "box", "layout": "horizontal", "margin": "sm",
                "contents": [
                    {"type": "text", "text": date_label, "size": "xs", "color": "#aaaaaa", "flex": 2},
                    {"type": "text", "text": "排班" if r['type'] == 'shift' else "獎金", "size": "xs", "color": "#ffffff", "flex": 3},
                    {"type": "text", "text": info, "size": "xs", "color": "#ffffff", "align": "end", "flex": 5}
                ]
            })

        return {
            "type": "bubble", "size": "mega",
            "styles": {"body": {"backgroundColor": "#121d2b"}},
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": f"💰 {month_label}薪資總覽", "weight": "bold", "color": "#ffffff", "size": "xl"},
                    {"type": "text", "text": username, "color": "#8b949e", "size": "sm", "margin": "xs"},
                    {"type": "box", "layout": "vertical", "margin": "xxl", "spacing": "sm", "contents": [
                        {"type": "text", "text": f"${total_amt:,.0f}", "size": "4xl", "color": "#03a9f4", "weight": "bold", "align": "center"},
                        {"type": "text", "text": f"共 {total_hrs:g} 小時" if total_hrs > 0 else "獎金累計", "size": "sm", "color": "#8b949e", "align": "center"},
                        {"type": "text", "text": f"{start_date} ~ {end_date}", "size": "xs", "color": "#8b949e", "align": "center"}
                    ]},
                    {"type": "separator", "margin": "xl", "color": "#2c3e50"},
                    {"type": "text", "text": "項目統計", "weight": "bold", "color": "#8b949e", "size": "sm", "margin": "lg"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": stat_rows or [{"type":"text","text":"暫無資料","color":"#555555"}]},
                    {"type": "separator", "margin": "xl", "color": "#2c3e50"},
                    {"type": "text", "text": "最近 10 筆", "weight": "bold", "color": "#8b949e", "size": "sm", "margin": "lg"},
                    {"type": "box", "layout": "vertical", "margin": "md", "contents": record_rows or [{"type":"text","text":"暫無資料","color":"#555555"}]},
                    {"type": "box", "layout": "vertical", "margin": "xl", "contents": [
                        {"type": "button", "action": {"type": "uri", "label": "查看全部薪資記錄 →", "uri": f"{WEB_BASE}/salary/"}, "style": "primary", "color": "#03a9f4", "height": "sm"}
                    ]}
                ]
            }
        }

    @staticmethod
    def build_salary_summary(username, start_date, end_date, total_amt, total_hrs, type_stats, records):
        bubble = FlexMessageService.build_salary_summary_bubble(username, start_date, end_date, total_amt, total_hrs, type_stats, records[:5])
        return {"type": "flex", "altText": f"{start_date[5:7]}月份薪資總覽", "contents": bubble}
