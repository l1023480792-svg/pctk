#!/usr/bin/env python3
"""每天0点采集 Steam / IGXE 起价，追加到 data.json。
依赖: pip install requests
定时(Linux/Mac crontab):  0 0 * * * /usr/bin/python3 /path/collect.py
Windows: 用“任务计划程序”每天 00:00 运行。
"""
import json, re, datetime, pathlib, requests
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).with_name("data.json")
UA = {"User-Agent": "Mozilla/5.0"}

# 添加物品: steam_name 为 Steam 市场的 market_hash_name
# igxe_url 为 IGXE 上该物品的搜索页/详情页网址(按价格升序，第一个价格即起价)
ITEMS = [
    {"id": "nightmare", "name": "梦魇武器箱",
     "steam_name": "Dreams & Nightmares Case",
     "igxe_url": "https://www.igxe.cn/market/csgo?keyword=梦魇武器箱&sort=3"},
    {"id": "fever", "name": "热潮武器箱",
     "steam_name": "Fever Case",
     "igxe_url": "https://www.igxe.cn/market/csgo?keyword=热潮武器箱&sort=3"},
]

def num(s):
    m = re.search(r"\d[\d,]*\.?\d*", s or "")
    return float(m.group().replace(",", "")) if m else None

def steam_price(name):
    r = requests.get("https://steamcommunity.com/market/priceoverview/",
        params={"appid": 730, "currency": 23, "market_hash_name": name},  # 23 = 人民币
        headers=UA, timeout=20)
    d = r.json()
    return num(d.get("lowest_price")) if d.get("success") else None

def igxe_price(url):
    # 尽力解析：取页面中第一个 ¥价格。IGXE 页面结构/反爬若变化，需要调整这里。
    html = requests.get(url, headers=UA, timeout=20).text
    m = re.search(r"[¥￥]\s*</?[^>]*>?\s*(\d+(?:\.\d+)?)", html) or re.search(r"[¥￥]\s*(\d+(?:\.\d+)?)", html)
    return float(m.group(1)) if m else None

def main():
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"items": []}
    by_id = {i["id"]: i for i in data["items"]}
    today = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    for it in ITEMS:
        rec = by_id.setdefault(it["id"], {"id": it["id"], "name": it["name"], "rows": []})
        try: s = steam_price(it["steam_name"])
        except Exception as e: s = None; print("steam fail", it["id"], e)
        try: g = igxe_price(it["igxe_url"])
        except Exception as e: g = None; print("igxe fail", it["id"], e)
        rec["rows"] = [r for r in rec["rows"] if r["date"] != today] + [{"date": today, "steam": s, "igxe": g}]
        rec["rows"].sort(key=lambda r: r["date"])
        print(it["name"], "steam", s, "igxe", g)
    data["items"] = list(by_id.values())
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

if __name__ == "__main__":
    main()
