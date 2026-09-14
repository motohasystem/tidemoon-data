#!/usr/bin/env python3
"""
気象庁 潮位表テキスト → ウォッチフェイス用 1日1JSON 変換

入力: https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{STATION}.txt
      1行 = 1日。固定長:
        1-72   毎時潮位 0時..23時 (3文字×24, cm, 欠測は空白)
        73-74  年(下2桁)  75-76 月  77-78 日  79-80 地点記号
        81-108 満潮 (時刻HHMM 4文字 + 潮位 3文字) × 4  無い枠は空白
        109-136 干潮 同上 × 4
出力: docs/{STATION}/{YYYY-MM-DD}.json
      { "start": <その日0時JSTのunix秒>, "series": "cm,cm,...(37個, +1000オフセット)",
        "extrema": "kind:分,kind:分,...", "hi": [["HH:MM",cm],...], "lo": [...] }
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
OFFSET_CM = 1000          # ウォッチフェイス側と合わせる（電文は常に正）
SPAN_HOURS = 37           # 今日0時〜翌12時

def fetch(year, station):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{station}.txt"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def parse_line(line):
    line = line.rstrip("\n").ljust(136)
    hourly = []
    for i in range(24):
        s = line[i*3:(i+1)*3].strip()
        hourly.append(int(s) if s else None)
    yy, mm, dd = int(line[72:74]), int(line[74:76]), int(line[76:78])
    year = 2000 + yy
    def ext(seg):
        out = []
        for k in range(4):
            # 時・分はそれぞれ2桁の空白詰め（" 628" = 06:28）なので strip せずに切り出す
            t = seg[k*7:k*7+4]; h = seg[k*7+4:k*7+7].strip()
            if t.strip() and h and t != "9999":
                out.append((int(t[:2]), int(t[2:]), int(h)))
        return out
    return {
        "date": datetime(year, mm, dd, tzinfo=JST),
        "hourly": hourly,
        "hi": ext(line[80:108]),
        "lo": ext(line[108:136]),
    }

def build_day(days, i):
    """days[i] を起点に 37 時間分をつくる（翌日があれば繋ぐ）"""
    today = days[i]
    nxt = days[i+1] if i + 1 < len(days) else None
    hourly = list(today["hourly"]) + (nxt["hourly"][:13] if nxt else [])
    hourly = hourly[:SPAN_HOURS]
    last = 0
    series = []
    for v in hourly:
        if v is not None: last = v
        series.append(max(0, last + OFFSET_CM))
    # 極値: 今日分 + 翌日12時まで
    extrema = []
    def add(kind, lst, day_off):
        for (h, m, cm) in lst:
            mins = day_off*1440 + h*60 + m
            if mins <= (SPAN_HOURS-1)*60:
                extrema.append((mins, kind, h, m, cm, day_off))
    add(0, today["hi"], 0); add(1, today["lo"], 0)
    if nxt:
        add(0, nxt["hi"], 1); add(1, nxt["lo"], 1)
    extrema.sort()
    return {
        "start": int(today["date"].timestamp()),
        "series": ",".join(str(v) for v in series),
        "extrema": ",".join(f"{k}:{mins}" for (mins, k, *_ ) in extrema),
        "hi": [[f"{h:02d}:{m:02d}", cm] for (_, k, h, m, cm, _d) in extrema if k == 0],
        "lo": [[f"{h:02d}:{m:02d}", cm] for (_, k, h, m, cm, _d) in extrema if k == 1],
    }

def main():
    station = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STATION", "KM")
    years = [int(y) for y in sys.argv[2:]] or [datetime.now(JST).year, datetime.now(JST).year + 1]
    days = []
    for y in years:
        try:
            txt = fetch(y, station)
        except Exception as e:
            print(f"skip {y}: {e}", file=sys.stderr); continue
        for line in txt.splitlines():
            if len(line.strip()) >= 78:
                days.append(parse_line(line))
    days.sort(key=lambda d: d["date"])
    outdir = os.path.join("docs", station)
    os.makedirs(outdir, exist_ok=True)
    for i in range(len(days)):
        data = build_day(days, i)
        with open(os.path.join(outdir, days[i]["date"].strftime("%Y-%m-%d") + ".json"), "w") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{station}: wrote {len(days)} days")

if __name__ == "__main__":
    main()
