#!/usr/bin/env python3
"""Old-style days from calendar.ortodox.md, one page per day, one request at a time.

Usage: tools/fetch_vechi.py 2026 2027 2028
Writes source/vechi/YYYY.json and resumes where it stopped.
"""
import datetime as dt
import html
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://calendar.ortodox.md/calendar/detailed/RO/{:02d}/{:02d}/{}"
HEADERS = {"User-Agent": "Ceaslovnicul calendar fetch (one request at a time)"}
DELAY = 1.2


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse(page):
    old = re.search(r"Stil vechi</div>\s*<div[^>]*>([^<]+)</div>", page)
    post = re.search(r'class="pure-g post">\s*<div[^>]*>(.*?)</div>', page, re.S)
    start = page.find('class="pure-g sfinti"')
    if not old or start < 0:
        raise ValueError("unexpected page")
    entries = re.findall(r'<a class="r r(\d)[^"]*"[^>]*>\s*<span>(.*?)</span>', page[start:], re.S)
    return {
        "old": plain(old.group(1)),
        "post": plain(post.group(1)) if post else "",
        "saints": [[int(rank), plain(text)] for rank, text in entries],
    }


def fetch(day):
    request = urllib.request.Request(URL.format(day.day, day.month, day.year), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def main():
    out = ROOT / "source" / "vechi"
    out.mkdir(parents=True, exist_ok=True)
    for year in map(int, sys.argv[1:]):
        path = out / f"{year}.json"
        days = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        day = dt.date(year, 1, 1)
        while day.year == year:
            key = day.strftime("%m-%d")
            if key not in days:
                for attempt in range(4):
                    try:
                        days[key] = parse(fetch(day))
                        break
                    except Exception as error:
                        print(year, key, "retry:", error, flush=True)
                        time.sleep(30 * (attempt + 1))
                else:
                    print("giving up at", year, key, flush=True)
                    path.write_text(json.dumps(days, ensure_ascii=False, indent=0), encoding="utf-8")
                    sys.exit(1)
                time.sleep(DELAY)
                if len(days) % 25 == 0:
                    path.write_text(json.dumps(days, ensure_ascii=False, indent=0), encoding="utf-8")
                    print(year, key, flush=True)
            day += dt.timedelta(days=1)
        path.write_text(json.dumps(days, ensure_ascii=False, indent=0), encoding="utf-8")
        print(year, "done", len(days), flush=True)


if __name__ == "__main__":
    main()
