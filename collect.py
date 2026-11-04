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
    # 方式1: priceoverview
    r = requests.get("https://steamcommunity.com/market/priceoverview/",
        params={"appid": 730, "currency": 23, "country": "CN", "market_hash_name": name},
        headers=H, timeout=20)
    print("  [steam priceoverview]", r.status_code, r.text[:150])
    try:
        d = r.json()
        if d and d.get("success"):
            return num(d.get("lowest_price") or d.get("median_price"))
    except Exception:
        pass
    # 方式2: 市场搜索接口
    r = requests.get("https://steamcommunity.com/market/search/render/",
        params={"query": name, "appid": 730, "norender": 1, "count": 10, "currency": 23},
        headers=H, timeout=20)
    print("  [steam search]", r.status_code, r.text[:150])
    try:
        for x in r.json().get("results", []):
            if x.get("hash_name") == name:
                return num(x.get("sell_price_text"))
    except Exception:
        pass
    return None

def igxe_price(url):
    html = requests.get(url, headers=H, timeout=20).text
    # ¥ 后可能隔着标签，小数部分也可能在单独的标签里
    pat = r"[¥￥]\s*(?:<[^>]*>\s*)*(\d+)(?:\s*(?:<[^>]*>\s*)*(\.\d{1,2}))?"
    ms = list(re.finditer(pat, html))
    print("  [igxe] 页面长度", len(html), "价格匹配数", len(ms))
    for m in ms[:3]:
        seg = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "|", html[max(0, m.start()-120):m.end()+60]))
        print("   片段:", seg[:200])
    if not ms:
        return None
    m = ms[0]
    return float(m.group(1) + (m.group(2) or ""))

def main():
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"items": []}
    by_id = {i["id"]: i for i in data["items"]}
    today = datetime.datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    for it in ITEMS:
        rec = by_id.setdefault(it["id"], {"id": it["id"], "name": it["name"], "rows": []})
        print(it["name"])
        try: s = steam_price(it["steam_name"])
        except Exception as e: s = None; print("  steam fail", e)
        try: g = igxe_price(it["igxe_url"])
        except Exception as e: g = None; print("  igxe fail", e)
        rec["rows"] = [r for r in rec["rows"] if r["date"] != today] + [{"date": today, "steam": s, "igxe": g}]
        rec["rows"].sort(key=lambda r: r["date"])
        print("  结果 steam", s, "igxe", g)
    data["items"] = list(by_id.values())
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

if __name__ == "__main__":
    main()
