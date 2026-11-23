"""티스토리 RSS를 읽어서 posts.json으로 저장한다. (GitHub Actions에서 실행)"""
import json, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

RSS = "https://ts2k.tistory.com/rss"
req = urllib.request.Request(RSS, headers={"User-Agent": "Mozilla/5.0 (posts.json updater)"})
root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
ch = root.find("channel")
posts = []
for it in ch.findall("item"):
    try:
        date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")
    except Exception:
        date = ""
    posts.append({
        "title": (it.findtext("title") or "").strip(),
        "link": (it.findtext("link") or "").strip(),
        "date": date,
        "categories": [c.text.strip() for c in it.findall("category") if c.text],
        "html": it.findtext("description") or "",
    })
data = {"blog": {"title": (ch.findtext("title") or "TS2k").strip(),
                 "desc": (ch.findtext("description") or "").strip(),
                 "link": "https://ts2k.tistory.com/"},
        "posts": posts}
with open("posts.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(f"{len(posts)} posts")
