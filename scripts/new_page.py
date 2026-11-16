#!/usr/bin/env python3
"""建立新的主題頁骨架，並登記到 data/pages.js。

用法（在專案根目錄執行）：
  python3 scripts/new_page.py <slug> --title "標題？" --category rain \
      --summary "一句話重點" --keywords "詞1,詞2"

會做三件事：
  1. 檢查 slug、分類、標題、摘要、關鍵字是否符合 AGENTS.md 的規則
  2. 由 templates/page.html 產生 wiki/<slug>.html（頁首、分類、日期自動填好）
  3. 把這一頁加進 data/pages.js（預設放在同分類最後一頁的後面）

剩下的 __大寫__ 佔位字依 AGENTS.md 填寫，最後執行 python3 scripts/check_site.py。
只用 Python 標準函式庫（3.8 以上）。Windows 沒有 python3 指令時改打 python。
"""
import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_JS = ROOT / "data" / "pages.js"
TEMPLATE = ROOT / "templates" / "page.html"
WIKI = ROOT / "wiki"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){1,4}$")
TITLE_MAX = 20
TITLE_SEGMENT_MAX = 11  # 手機上 h1 一行約 11 字，標題只在「，」「、」換行
SUMMARY_MIN, SUMMARY_MAX = 20, 60
KEYWORDS_MIN, KEYWORDS_MAX = 2, 6

HEADER = (
    "// data/pages.js：全站頁面清單（首頁目錄、搜尋、上一篇／下一篇都從這裡產生）\n"
    "// 規則見 AGENTS.md 4.1：陣列內容必須是合法 JSON；陣列順序＝閱讀順序，同分類放在一起。\n"
    "// 新增頁面請用：python3 scripts/new_page.py <slug> --title ... --category ... --summary ...\n"
)


def load_manifest(text):
    """取出 window.APO_CATEGORIES 與 window.APO_PAGES 兩個 JSON 陣列。"""

    def grab(name):
        match = re.search(r"window\.%s\s*=\s*" % name, text)
        if not match:
            raise ValueError("data/pages.js 裡找不到 window.%s" % name)
        value, _ = json.JSONDecoder().raw_decode(text, match.end())
        return value

    return grab("APO_CATEGORIES"), grab("APO_PAGES")


def dump_manifest(categories, pages):
    def block(name, items):
        if not items:
            return "window.%s = [];\n" % name
        rows = ",\n".join("  " + json.dumps(item, ensure_ascii=False) for item in items)
        return "window.%s = [\n%s\n];\n" % (name, rows)

    return HEADER + "\n" + block("APO_CATEGORIES", categories) + "\n" + block("APO_PAGES", pages)


def fail(message):
    print("[無法建立] " + message)
    sys.exit(1)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="建立新的主題頁骨架並登記到 data/pages.js")
    parser.add_argument("slug", help="英文小寫＋連字號，2～5 個字，例如 debris-flow-alerts")
    parser.add_argument("--title", required=True, help="讀者會問的問題，最多 20 字")
    parser.add_argument("--category", required=True, help="分類 id：basics、rain、home、aid")
    parser.add_argument("--summary", required=True, help="一句話給答案，20～60 字")
    parser.add_argument("--keywords", required=True, help="2～6 個搜尋用詞，用逗號隔開")
    parser.add_argument("--after", help="放在哪一頁後面（slug）；不填就放在同分類最後")
    parser.add_argument("--date", help="最後更新日期 YYYY-MM-DD，不填就用今天")
    args = parser.parse_args()

    categories, pages = load_manifest(PAGES_JS.read_text(encoding="utf-8"))
    category_ids = [c["id"] for c in categories]
    slugs = [p["slug"] for p in pages]

    slug = args.slug.strip()
    title = args.title.strip()
    summary = args.summary.strip()
    keywords = [k.strip() for k in re.split(r"[,，、]", args.keywords) if k.strip()]
    date = args.date or datetime.date.today().isoformat()

    if not SLUG_RE.match(slug):
        fail("slug「%s」不符合規則：英文小寫單字＋連字號，2～5 個字。" % slug)
    if slug in slugs or (WIKI / (slug + ".html")).exists():
        fail("slug「%s」已經存在。" % slug)
    if args.category not in category_ids:
        fail("分類「%s」不存在，只能用：%s。新增分類要先問使用者。" % (args.category, "、".join(category_ids)))
    if not 1 <= len(title) <= TITLE_MAX:
        fail("標題要 1～%d 字，現在是 %d 字。" % (TITLE_MAX, len(title)))
    longest = max(len(part) for part in re.split(r"[，、]", title))
    if longest > TITLE_SEGMENT_MAX:
        fail("標題每段（用「，」或「、」分開）最多 %d 字，現在最長一段 %d 字。" % (TITLE_SEGMENT_MAX, longest))
    if not SUMMARY_MIN <= len(summary) <= SUMMARY_MAX:
        fail("摘要要 %d～%d 字，現在是 %d 字。" % (SUMMARY_MIN, SUMMARY_MAX, len(summary)))
    if not KEYWORDS_MIN <= len(keywords) <= KEYWORDS_MAX:
        fail("關鍵字要 %d～%d 個，現在是 %d 個。" % (KEYWORDS_MIN, KEYWORDS_MAX, len(keywords)))
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        fail("日期「%s」不是 YYYY-MM-DD。" % date)
    if args.after and args.after not in slugs:
        fail("--after 指定的頁面「%s」不在清單裡。" % args.after)

    category = next(c for c in categories if c["id"] == args.category)

    # 1. 由範本產生頁面
    page_html = TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "__SLUG__": slug,
        "__TITLE__": html.escape(title, quote=False),
        "__SUMMARY__": html.escape(summary, quote=True),
        "__DATE__": date,
        "__CATEGORY_ID__": category["id"],
        "__CATEGORY_NAME__": html.escape(category["name"], quote=False),
    }.items():
        page_html = page_html.replace(key, value)
    WIKI.mkdir(exist_ok=True)
    (WIKI / (slug + ".html")).write_text(page_html, encoding="utf-8")

    # 2. 登記到清單：同分類放在一起，順序依 APO_CATEGORIES
    entry = {
        "slug": slug,
        "title": title,
        "category": category["id"],
        "summary": summary,
        "keywords": keywords,
        "updated": date,
    }
    if args.after:
        position = slugs.index(args.after) + 1
    else:
        rank = category_ids.index(category["id"])
        same = [i for i, p in enumerate(pages) if p["category"] == category["id"]]
        later = [i for i, p in enumerate(pages)
                 if p["category"] in category_ids and category_ids.index(p["category"]) > rank]
        position = same[-1] + 1 if same else (later[0] if later else len(pages))
    pages.insert(position, entry)
    PAGES_JS.write_text(dump_manifest(categories, pages), encoding="utf-8")

    print("已建立 wiki/%s.html，並登記到 data/pages.js（第 %d 頁，分類：%s）。"
          % (slug, position + 1, category["name"]))
    print("接下來：")
    print("  1. 依 AGENTS.md 第三、四節填完所有 __大寫__ 佔位字，刪掉「範本：」註解")
    print("  2. 在 1～3 個相關的既有頁面「相關頁面」加上這一頁")
    print("  3. 執行 python3 scripts/check_site.py，修到 0 個錯誤")
    print("  4. 在 log.md 檔尾追加一筆紀錄")


if __name__ == "__main__":
    main()
