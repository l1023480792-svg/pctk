#!/usr/bin/env python3
"""每天0点采集 Steam / IGXE 起价，追加到 data.json。依赖: requests"""
import json, re, datetime, pathlib, requests
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).with_name("data.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
     "Accept-Language": "zh-CN,zh;q=0.9"}

ITEMS = [
    {"id": "nightmare", "name": "梦魇武器箱", "steam_name": "Dreams & Nightmares Case",
     "igxe_url": "https://www.igxe.cn/market/csgo?keyword=梦魇武器箱&sort=3"},
    {"id": "fever", "name": "热潮武器箱", "steam_name": "Fever Case",
     "igxe_url": "https://www.igxe.cn/market/csgo?keyword=热潮武器箱&sort=3"},
]

def num(s):
    m = re.search(r"\d[\d,]*\.?\d*", str(s or ""))
    return float(m.group().replace(",", "")) if m else None

def steam_price(name):
    import os, time
    px = os.environ.get("STEAM_PROXY")
    proxies = {"http": px, "https": px} if px else None
    tries = [
        ("priceoverview", "https://steamcommunity.com/market/priceoverview/",
         {"appid": 730, "currency": 23, "country": "CN", "market_hash_name": name},
         lambda d: d.get("success") and num(d.get("lowest_price") or d.get("median_price"))),
        ("search", "https://steamcommunity.com/market/search/render/",
         {"query": name, "appid": 730, "norender": 1, "count": 10, "currency": 23},
         lambda d: next((num(x.get("sell_price_text")) for x in d.get("results", []) if x.get("hash_name") == name), None)),
    ]
    for attempt in range(3):
        for label, url, params, pick in tries:
            try:
                r = requests.get(url, params=params, headers=H, timeout=20, proxies=proxies)
                print("  [steam %s] 第%d次" % (label, attempt + 1), r.status_code, r.text[:100])
                if r.status_code == 200:
                    v = pick(r.json() or {})
                    if v: return v
            except Exception as e:
                print("  [steam %s] 异常" % label, e)
        time.sleep(10 * (attempt + 1))
    return None

def igxe_price(url, name):
    html = requests.get(url, headers=H, timeout=20).text
    T = r"(?:\s*<[^>]*>\s*)*"
    pat = r"[¥￥]" + T + r"(\d+)(?:" + T + r"\." + T + r"(\d{1,2}))?"
    ms = list(re.finditer(pat, html))
    print("  [igxe] 页面长度", len(html), "价格匹配数", len(ms))
    for m in ms:
        # 只取物品名后面紧跟的价格，跳过无关的 ¥0.00
        if name in html[max(0, m.start() - 300):m.start()]:
            v = float(m.group(1) + "." + (m.group(2) or "0"))
            if v > 0:
                return v
    return None

def main():
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"items": []}
    by_id = {i["id"]: i for i in data["items"]}
    today = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    for it in ITEMS:
        rec = by_id.setdefault(it["id"], {"id": it["id"], "name": it["name"], "rows": []})
        print(it["name"])
        try: s = steam_price(it["steam_name"])
        except Exception as e: s = None; print("  steam fail", e)
        try: g = igxe_price(it["igxe_url"], it["name"])
        except Exception as e: g = None; print("  igxe fail", e)
        rec["rows"] = [r for r in rec["rows"] if r["date"] != today] + [{"date": today, "steam": s, "igxe": g}]
        rec["rows"].sort(key=lambda r: r["date"])
        print("  结果 steam", s, "igxe", g)
    data["items"] = list(by_id.values())
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

if __name__ == "__main__":
    main()
