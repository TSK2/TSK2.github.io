"""티스토리 RSS + 각 글 페이지를 읽어서 posts.json으로 저장한다. (GitHub Actions에서 실행)

- RSS 설명(description)은 요약만 들어오므로, 글 페이지에서 본문 전체를 가져온다.
- 티스토리가 잠깐 응답하지 않아도 재시도하고, 끝내 실패하면 기존 posts.json을 그대로 둔다.
"""
import json, re, sys, time, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

BLOG = "https://ts2k.tistory.com"
UA = {"User-Agent": "Mozilla/5.0 (posts.json updater)"}


def get(url, tries=4):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:
            print(f"  재시도 {n + 1}/{tries}: {url} ({e})")
            time.sleep(5 * (n + 1))
    return None


class Body(HTMLParser):
    """<div class="... contents_style ..."> 안쪽 HTML을 그대로 잘라낸다."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0; self.start = None; self.end = None; self.raw = ""

    def handle_starttag(self, tag, attrs):
        if self.end is not None or tag != "div":
            return
        if self.start is None:
            if "contents_style" in (dict(attrs).get("class") or ""):
                self.start = self.offset_after(); self.depth = 1
        else:
            self.depth += 1

    def handle_endtag(self, tag):
        if self.start is not None and self.end is None and tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.end = self.pos()

    def pos(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def offset_after(self):
        return self.pos() + len(self.get_starttag_text())

    def extract(self, html):
        self.lines = [0]
        for ln in html.split("\n"):
            self.lines.append(self.lines[-1] + len(ln) + 1)
        self.feed(html)
        return html[self.start:self.end] if self.start is not None and self.end else None


def clean(html):
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return html.strip()


raw = get(BLOG + "/rss")
if raw is None:
    print("RSS를 가져오지 못해 기존 posts.json을 유지합니다.")
    sys.exit(0)

ch = ET.fromstring(raw).find("channel")
try:
    old = {p["link"]: p for p in json.load(open("posts.json", encoding="utf-8"))["posts"]}
except Exception:
    old = {}

posts = []
for it in ch.findall("item"):
    link = (it.findtext("link") or "").strip()
    try:
        date = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d")
    except Exception:
        date = ""
    page = get(link)
    body = Body().extract(page.decode("utf-8", "replace")) if page else None
    if body:
        html, full = clean(body), True
    elif old.get(link, {}).get("full"):
        html, full = old[link]["html"], True          # 이번에 못 가져오면 지난번 본문 유지
    else:
        html, full = it.findtext("description") or "", False
    posts.append({
        "title": (it.findtext("title") or "").strip(),
        "link": link,
        "date": date,
        "categories": [c.text.strip() for c in it.findall("category") if c.text],
        "full": full,
        "html": html,
    })
    print(f"  {'본문' if full else '요약'} | {posts[-1]['title']}")

data = {"blog": {"title": (ch.findtext("title") or "TS2k").strip(),
                 "desc": (ch.findtext("description") or "").strip(),
                 "link": BLOG + "/"},
        "posts": posts}
with open("posts.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print(f"{len(posts)} posts")
