#!/usr/bin/env python3
"""檢查整個網站是否符合 AGENTS.md 的規則（交付前必跑）。

用法（在專案根目錄執行）：
  python3 scripts/check_site.py            # 有錯誤時結束碼為 1
  python3 scripts/check_site.py --strict   # 連警告也當成錯誤

檢查內容：
  - 必要檔案、CLAUDE.md 是否匯入 AGENTS.md、.md 檔沒有 Jekyll 樣板語法
  - data/pages.js：合法 JSON、欄位、slug 命名、分類、字數、日期，以及和 wiki/ 檔案一一對應
  - 每個主題頁：區塊順序、標題與摘要和清單一致、出處格式、相關頁面、佔位字、
    inline style 或 script、SVG 色碼、圖表說明、站內連結
  - raw/：檔名與資料卡欄位
  - 健檢（警告）：孤兒頁、沒有被引用的 raw 檔、篇幅、阿坡伯說裡的數字
只用 Python 標準函式庫（3.8 以上）。Windows 沒有 python3 指令時改打 python。
"""
import argparse
import datetime
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE_NAME = "阿坡伯山坡地小百科"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){1,4}$")
LAW_FILE_RE = re.compile(r"^[A-Z][0-9]{7}\.md$")
WEB_FILE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-[0-9]{8}\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER_RE = re.compile(r"__[A-Z0-9_]+__")
PAGE_KEYS = ["slug", "title", "category", "summary", "keywords", "updated"]
SECTION_ORDER = ["page-head", "apo-says", "explain", "todo", "sources", "related"]
REQUIRED_FILES = [
    "AGENTS.md", "CLAUDE.md", "README.md", "log.md", "index.html", ".nojekyll",
    "data/pages.js", "assets/site.css", "assets/site.js", "assets/favicon.svg",
    "templates/page.html", "scripts/new_page.py", "raw/README.md",
]
TEMPLATE_KEYS = ["__SLUG__", "__TITLE__", "__SUMMARY__", "__DATE__", "__CATEGORY_ID__", "__CATEGORY_NAME__"]
PAGE_SCRIPTS = ["../data/pages.js", "../assets/site.js"]
COLOR_ATTRS = {"fill", "stroke", "color", "stop-color", "flood-color", "lighting-color"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "source", "track", "wbr"}
CJK_RE = re.compile(r"[㐀-鿿豈-﫿]")


# ---------------------------------------------------------------- 小型 DOM
class Node:
    def __init__(self, tag, attrs, parent, line):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.line = line
        self.children = []

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]

    def iter(self):
        yield self
        for child in self.elements():
            yield from child.iter()

    def find_all(self, tag=None, cls=None, **attrs):
        out = []
        for node in self.iter():
            if node is self:
                continue
            if tag and node.tag != tag:
                continue
            if cls and cls not in node.classes():
                continue
            if any(node.attrs.get(k.replace("_", "-")) != v for k, v in attrs.items()):
                continue
            out.append(node)
        return out

    def find(self, tag=None, cls=None, **attrs):
        found = self.find_all(tag, cls, **attrs)
        return found[0] if found else None

    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def text(self):
        parts = []
        for child in self.children:
            if isinstance(child, Node):
                if child.tag not in ("script", "style"):
                    parts.append(child.text())
            else:
                parts.append(child)
        return "".join(parts)

    def clean_text(self):
        return re.sub(r"\s+", " ", self.text()).strip()

    def has_ancestor(self, tag=None, cls=None):
        node = self.parent
        while node is not None:
            if (tag is None or node.tag == tag) and (cls is None or cls in node.classes()):
                return True
            node = node.parent
        return False


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None, 0)
        self.current = self.root
        self.comments = []

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs},
                    self.current, self.getpos()[0])
        self.current.children.append(node)
        if tag not in VOID_TAGS:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs},
                    self.current, self.getpos()[0])
        self.current.children.append(node)

    def handle_endtag(self, tag):
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent

    def handle_data(self, data):
        self.current.children.append(data)

    def handle_comment(self, data):
        self.comments.append((self.getpos()[0], data.strip()))


def parse_html(path):
    builder = TreeBuilder()
    builder.feed(path.read_text(encoding="utf-8"))
    builder.close()
    return builder.root, builder.comments


# ---------------------------------------------------------------- 結果收集
class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, message):
        self.errors.append("%s：%s" % (where, message))

    def warn(self, where, message):
        self.warnings.append("%s：%s" % (where, message))


def rel(path):
    return path.relative_to(ROOT).as_posix()


def load_manifest(report):
    path = ROOT / "data" / "pages.js"
    text = path.read_text(encoding="utf-8")
    result = {}
    for name in ("APO_CATEGORIES", "APO_PAGES"):
        match = re.search(r"window\.%s\s*=\s*" % name, text)
        if not match:
            report.error("data/pages.js", "找不到 window.%s" % name)
            return None, None
        try:
            result[name], _ = json.JSONDecoder().raw_decode(text, match.end())
        except json.JSONDecodeError as exc:
            report.error("data/pages.js", "window.%s 不是合法 JSON（%s）。鍵名要加雙引號、不能有結尾逗號。" % (name, exc))
            return None, None
    return result["APO_CATEGORIES"], result["APO_PAGES"]


# ---------------------------------------------------------------- 各項檢查
def check_files(report):
    for name in REQUIRED_FILES:
        if not (ROOT / name).exists():
            report.error(name, "必要檔案不存在")
    claude = ROOT / "CLAUDE.md"
    if claude.exists():
        lines = [line.strip() for line in claude.read_text(encoding="utf-8").splitlines()]
        if "@AGENTS.md" not in lines:
            report.error("CLAUDE.md", "要有一行單獨的 @AGENTS.md 來匯入規則")
    for md in sorted(ROOT.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        if "{{" in text or "{%" in text:
            report.error(rel(md), "Markdown 裡不能有 Jekyll 樣板語法（兩個大括號或大括號加百分比）")
    template = ROOT / "templates" / "page.html"
    if template.exists():
        text = template.read_text(encoding="utf-8")
        for key in TEMPLATE_KEYS:
            if key not in text:
                report.error("templates/page.html", "少了 new_page.py 需要的佔位字 %s" % key)


def check_manifest(report, categories, pages):
    where = "data/pages.js"
    category_ids = []
    for cat in categories:
        if set(cat) != {"id", "name", "desc"}:
            report.error(where, "分類欄位要剛好是 id、name、desc：%s" % cat)
            continue
        if not re.match(r"^[a-z]+$", cat["id"]):
            report.error(where, "分類 id「%s」要是英文小寫" % cat["id"])
        category_ids.append(cat["id"])
    if len(set(category_ids)) != len(category_ids):
        report.error(where, "分類 id 重複")

    seen = set()
    order = []
    today = datetime.date.today()
    for i, page in enumerate(pages, 1):
        tag = "%s 第 %d 筆" % (where, i)
        if list(page) != PAGE_KEYS:
            report.error(tag, "欄位要依序是 %s" % "、".join(PAGE_KEYS))
            if not all(k in page for k in PAGE_KEYS):
                continue
        slug = page["slug"]
        if not SLUG_RE.match(slug):
            report.error(tag, "slug「%s」不符合命名規則（英文小寫＋連字號，2～5 個字）" % slug)
        if slug in seen:
            report.error(tag, "slug「%s」重複" % slug)
        seen.add(slug)
        if page["category"] not in category_ids:
            report.error(tag, "分類「%s」不存在" % page["category"])
        if not 1 <= len(page["title"]) <= 20:
            report.error(tag, "標題要 1～20 字（現在 %d 字）" % len(page["title"]))
        longest = max(len(part) for part in re.split(r"[，、]", page["title"]))
        if longest > 11:
            report.error(tag, "標題每段（用「，」或「、」分開）最多 11 字，手機才不會把詞拆開（現在最長一段 %d 字）" % longest)
        if not 20 <= len(page["summary"]) <= 60:
            report.error(tag, "摘要要 20～60 字（現在 %d 字）" % len(page["summary"]))
        keywords = page["keywords"]
        if not (isinstance(keywords, list) and 2 <= len(keywords) <= 6
                and all(isinstance(k, str) and k.strip() for k in keywords)):
            report.error(tag, "keywords 要是 2～6 個詞的陣列")
        if not DATE_RE.match(str(page["updated"])):
            report.error(tag, "updated 要是 YYYY-MM-DD")
        else:
            try:
                if datetime.date.fromisoformat(page["updated"]) > today:
                    report.warn(tag, "updated 是未來的日期")
            except ValueError:
                report.error(tag, "updated 不是有效日期")
        if not order or order[-1] != page["category"]:
            order.append(page["category"])
    if len(order) != len(set(order)):
        report.warn(where, "同一分類的頁面沒有放在一起（閱讀順序會跳來跳去）")

    files = {p.stem for p in (ROOT / "wiki").glob("*.html")}
    for slug in sorted(seen - files):
        report.error(where, "清單裡有「%s」，但 wiki/%s.html 不存在" % (slug, slug))
    for slug in sorted(files - seen):
        report.error("wiki/%s.html" % slug, "這一頁沒有登記在 data/pages.js")
    return category_ids


def check_links(report, where, path, root, ids):
    """站內相對連結與資源都要存在；同頁錨點要有對應的 id。"""
    for node in root.iter():
        for attr in ("href", "src"):
            value = node.attrs.get(attr)
            if not value:
                continue
            parts = urlsplit(value)
            if parts.scheme in ("http", "https"):
                continue
            if parts.scheme or value.startswith("//"):
                if parts.scheme not in ("mailto", "tel"):
                    report.error(where, "第 %d 行：不支援的連結 %s" % (node.line, value))
                continue
            if value.startswith("/"):
                report.error(where, "第 %d 行：不要用 / 開頭的絕對路徑（%s），GitHub Pages 會找不到" % (node.line, value))
                continue
            if not parts.path:
                if parts.fragment and parts.fragment not in ids:
                    report.error(where, "第 %d 行：頁內找不到 #%s" % (node.line, parts.fragment))
                continue
            target = (path.parent / parts.path).resolve()
            if not target.exists():
                report.error(where, "第 %d 行：連結的檔案不存在 %s" % (node.line, value))


def check_page(report, path, page, pages_by_slug, category_names, inbound, cited_raw):
    where = rel(path)
    root, comments = parse_html(path)
    text = path.read_text(encoding="utf-8")
    slug, title, summary = page["slug"], page["title"], page["summary"]

    html_node = root.find("html")
    if not html_node or html_node.attrs.get("lang") != "zh-Hant-TW":
        report.error(where, '<html> 要有 lang="zh-Hant-TW"')
    body = root.find("body")
    if not body or body.attrs.get("data-page") != slug:
        report.error(where, '<body> 的 data-page 要等於 slug「%s」' % slug)

    title_node = root.find("title")
    expected_title = "%s｜%s" % (title, SITE_NAME)
    if not title_node or title_node.clean_text() != expected_title:
        report.error(where, "<title> 要是「%s」" % expected_title)
    desc = root.find("meta", name="description")
    if not desc or desc.attrs.get("content") != summary:
        report.error(where, "meta description 要和清單的 summary 一字不差")

    stylesheets = [n.attrs.get("href") for n in root.find_all("link") if n.attrs.get("rel") == "stylesheet"]
    if "../assets/site.css" not in stylesheets:
        report.error(where, "要載入 ../assets/site.css")
    scripts = root.find_all("script")
    if [s.attrs.get("src") for s in scripts] != PAGE_SCRIPTS:
        report.error(where, "頁面只能載入 ../data/pages.js 與 ../assets/site.js，不能寫自己的 script")
    if root.find("style"):
        report.error(where, "頁面不能有 <style>，樣式一律寫在 assets/site.css")

    for node in root.iter():
        if "style" in node.attrs:
            report.error(where, "第 %d 行：不能用 inline style" % node.line)
        for attr in node.attrs:
            if attr.startswith("on"):
                report.error(where, "第 %d 行：不能用 %s 這類 inline 事件" % (node.line, attr))
        for attr in COLOR_ATTRS & set(node.attrs):
            if node.attrs[attr] not in ("none", "currentColor", "transparent"):
                report.error(where, "第 %d 行：不能直接寫顏色 %s=\"%s\"，請改用 svg-* class" % (node.line, attr, node.attrs[attr]))

    for found in sorted(set(PLACEHOLDER_RE.findall(text))):
        report.error(where, "還有沒填的佔位字 %s" % found)
    for line, comment in comments:
        if comment.startswith("範本："):
            report.error(where, "第 %d 行：「範本：」註解要刪掉" % line)

    article = root.find("article", cls="topic")
    if not article:
        report.error(where, "找不到 <article class=\"topic\">")
        return
    order = []
    for child in article.elements():
        key = child.attrs.get("id") or next(iter(child.classes() & set(SECTION_ORDER)), child.tag)
        order.append(key)
    if order != SECTION_ORDER:
        report.error(where, "article 裡的區塊順序要是 %s（現在是 %s）" % (" → ".join(SECTION_ORDER), " → ".join(order)))

    head = article.find("header", cls="page-head")
    if head:
        h1s = root.find_all("h1")
        if len(h1s) != 1 or h1s[0].clean_text() != title:
            report.error(where, "要剛好一個 h1，文字等於清單 title「%s」" % title)
        lead = head.find("p", cls="lead")
        if not lead or lead.clean_text() != summary:
            report.error(where, "p.lead 要和清單 summary 一字不差")
        time = head.find("time")
        if not time or time.attrs.get("datetime") != page["updated"] or time.clean_text() != page["updated"]:
            report.error(where, "<time> 的 datetime 與文字都要等於清單 updated（%s）" % page["updated"])
        crumb = head.find("a", href="../index.html#cat-%s" % page["category"])
        if not crumb or crumb.clean_text() != category_names.get(page["category"]):
            report.error(where, "麵包屑的分類要連到 ../index.html#cat-%s，文字是「%s」"
                         % (page["category"], category_names.get(page["category"])))

    apo = article.find("aside", cls="apo-says")
    if apo:
        line = apo.find("p", cls="apo-says__line")
        if not line or not line.clean_text():
            report.error(where, "阿坡伯說要有一句話（p.apo-says__line）")
        elif re.search(r"\d", line.clean_text()):
            report.warn(where, "阿坡伯說裡有數字；數字和事實應該寫在正文並附出處")
        elif len(line.clean_text()) > 60:
            report.warn(where, "阿坡伯說超過 60 字，請縮成一兩句")

    explain = article.find("section", id="explain")
    if explain:
        count = len(explain.find_all("h2"))
        if not 2 <= count <= 4:
            report.error(where, "說明本文要有 2～4 個 h2 小節（現在 %d 個）" % count)

    todo = article.find("section", id="todo")
    if todo:
        h2 = todo.find("h2")
        if not h2 or h2.clean_text() != "你可以怎麼做":
            report.error(where, "#todo 的標題要是「你可以怎麼做」")
        lists = [n for n in todo.elements() if n.tag in ("ol", "ul")
                 and n.classes() & {"steps", "checklist"}]
        items = sum(len([li for li in lst.elements() if li.tag == "li"]) for lst in lists)
        if not lists:
            report.error(where, "#todo 要用 ol.steps 或 ul.checklist")
        elif not 3 <= items <= 6:
            report.error(where, "#todo 要有 3～6 項行動（現在 %d 項）" % items)

    sources = article.find("section", id="sources")
    if sources:
        h2 = sources.find("h2")
        if not h2 or h2.clean_text() != "資料來源":
            report.error(where, "#sources 的標題要是「資料來源」")
        listing = sources.find("ol", cls="sources")
        items = [li for li in listing.elements() if li.tag == "li"] if listing else []
        if not items:
            report.error(where, "#sources 要有 ol.sources，而且至少一筆")
        for n, li in enumerate(items, 1):
            if not any(a.attrs.get("href", "").startswith("https://") for a in li.find_all("a")):
                report.error(where, "第 %d 筆來源缺少 https 官方網址" % n)
            raws = li.find_all("a", cls="raw")
            if not raws:
                report.error(where, "第 %d 筆來源缺少 a.raw 原始資料連結" % n)
            for a in raws:
                href = a.attrs.get("href", "")
                if not href.startswith("../raw/"):
                    report.error(where, "第 %d 筆來源的 raw 連結要以 ../raw/ 開頭" % n)
                    continue
                if a.clean_text() != href[3:]:
                    report.error(where, "第 %d 筆來源的 raw 連結文字要寫成 %s" % (n, href[3:]))
                target = (path.parent / href).resolve()
                if target.exists():
                    cited_raw.add(target)

    related = article.find("section", id="related")
    if related:
        h2 = related.find("h2")
        if not h2 or h2.clean_text() != "相關頁面":
            report.error(where, "#related 的標題要是「相關頁面」")
        listing = related.find("ul", cls="related")
        links = listing.find_all("a") if listing else []
        if not 1 <= len(links) <= 3:
            report.error(where, "相關頁面要有 1～3 個連結（現在 %d 個）" % len(links))
        for a in links:
            href = a.attrs.get("href", "")
            target = href[:-5] if href.endswith(".html") else None
            if target not in pages_by_slug or target == slug:
                report.error(where, "相關頁面「%s」要連到其他已登記的主題頁" % href)
                continue
            if a.clean_text() != pages_by_slug[target]["title"]:
                report.error(where, "相關頁面連結文字要等於對方標題「%s」" % pages_by_slug[target]["title"])
            inbound.setdefault(target, set()).add(slug)

    pager = root.find("nav", cls="pager")
    if not pager:
        report.error(where, "要保留 <nav class=\"pager\">（上一篇／下一篇由 site.js 產生）")
    elif pager.elements():
        report.error(where, "nav.pager 要保持空白，內容由 site.js 產生")
    foot = root.find("footer", cls="site-foot")
    if not foot or "119" not in foot.clean_text():
        report.error(where, "頁尾的 119 緊急提醒不能刪")

    for img in root.find_all("img"):
        if not img.attrs.get("alt"):
            report.error(where, "第 %d 行：<img> 要有 alt" % img.line)
    for figure in article.find_all("figure"):
        if "diagram" not in figure.classes():
            report.error(where, "第 %d 行：圖要用 figure.diagram" % figure.line)
        svg = figure.find("svg")
        if not svg or svg.attrs.get("role") != "img" or not svg.attrs.get("aria-label"):
            report.error(where, "第 %d 行：figure.diagram 的 svg 要有 role=\"img\" 與 aria-label" % figure.line)
        if not figure.find("figcaption"):
            report.error(where, "第 %d 行：figure.diagram 要有 figcaption" % figure.line)
    for svg in article.find_all("svg"):
        if not svg.has_ancestor("figure", "diagram"):
            report.error(where, "第 %d 行：svg 要放在 figure.diagram 裡" % svg.line)
    for table in article.find_all("table"):
        if "data" not in table.classes() or not table.has_ancestor("div", "table-wrap"):
            report.error(where, "第 %d 行：表格要用 div.table-wrap > table.data" % table.line)
        if not table.find("caption"):
            report.error(where, "第 %d 行：表格要有 caption" % table.line)
        if any("scope" not in th.attrs for th in table.find_all("th")):
            report.warn(where, "第 %d 行：表頭 th 最好加 scope" % table.line)
    for badge in article.find_all("span", cls="badge"):
        if not badge.clean_text():
            report.error(where, "第 %d 行：燈號標籤要有文字，不能只靠顏色" % badge.line)

    ids = {n.attrs["id"] for n in root.iter() if "id" in n.attrs}
    check_links(report, where, path, root, ids)

    body_text = "".join(sec.clean_text() for sec in (explain, todo) if sec is not None)
    cjk = len(CJK_RE.findall(body_text))
    if cjk < 400:
        report.warn(where, "本文（說明＋你可以怎麼做）只有約 %d 字，建議 500～1,500 字" % cjk)
    elif cjk > 2200:
        report.warn(where, "本文約 %d 字，太長了，考慮拆成兩頁" % cjk)


def check_index(report, categories):
    path = ROOT / "index.html"
    if not path.exists():
        return
    root, _ = parse_html(path)
    where = "index.html"
    if root.find("body") is None or root.find("body").attrs.get("data-page") != "index":
        report.error(where, '<body> 要有 data-page="index"')
    for needed in ("catalog", "search", "search-status", "about"):
        if not root.find(id=needed):
            report.error(where, "找不到 id=\"%s\"" % needed)
    if [s.attrs.get("src") for s in root.find_all("script")] != ["data/pages.js", "assets/site.js"]:
        report.error(where, "首頁只能載入 data/pages.js 與 assets/site.js")
    for node in root.iter():
        if "style" in node.attrs:
            report.error(where, "第 %d 行：不能用 inline style" % node.line)
    ids = {n.attrs["id"] for n in root.iter() if "id" in n.attrs}
    ids |= {"cat-" + c["id"] for c in categories}  # 由 site.js 產生的分類錨點
    check_links(report, where, path, root, ids)


def check_raw(report):
    files = []
    for folder, pattern, example in (("laws", LAW_FILE_RE, "D0120014.md"),
                                     ("web", WEB_FILE_RE, "ardswc-faq-20261114.md")):
        for path in sorted((ROOT / "raw" / folder).glob("*")):
            where = rel(path)
            if not pattern.match(path.name):
                report.error(where, "檔名不符合規則（例：raw/%s/%s）" % (folder, example))
            text = path.read_text(encoding="utf-8")
            if not re.search(r"^\| 原始出處 \| https?://\S+ \|$", text, re.M):
                report.error(where, "資料卡缺少「| 原始出處 | 網址 |」")
            if not re.search(r"^\| 擷取日期 \| \d{4}-\d{2}-\d{2} \|$", text, re.M):
                report.error(where, "資料卡缺少「| 擷取日期 | YYYY-MM-DD |」")
            files.append(path.resolve())
    return files


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="檢查網站是否符合 AGENTS.md")
    parser.add_argument("--strict", action="store_true", help="連警告也當成錯誤")
    args = parser.parse_args()

    report = Report()
    check_files(report)
    categories, pages = load_manifest(report)
    raw_files = check_raw(report)
    if categories is None:
        return finish(report, 0, len(raw_files), args.strict)

    check_manifest(report, categories, pages)
    category_names = {c["id"]: c["name"] for c in categories if "id" in c and "name" in c}
    pages_by_slug = {p["slug"]: p for p in pages if "slug" in p}
    inbound, cited_raw = {}, set()
    checked = 0
    for page in pages:
        path = ROOT / "wiki" / ("%s.html" % page.get("slug"))
        if not path.exists() or not all(k in page for k in PAGE_KEYS):
            continue
        check_page(report, path, page, pages_by_slug, category_names, inbound, cited_raw)
        checked += 1
    check_index(report, categories)

    # 健檢（LLM Wiki 的 lint）
    if len(pages_by_slug) > 1:
        for slug in pages_by_slug:
            if not inbound.get(slug):
                report.warn("wiki/%s.html" % slug, "沒有其他頁面的「相關頁面」連到這一頁（孤兒頁）")
    for path in raw_files:
        if path not in cited_raw:
            report.warn(rel(path), "沒有任何主題頁引用這個原始資料")
    return finish(report, checked, len(raw_files), args.strict)


def finish(report, pages_checked, raw_checked, strict):
    print("%s：規則檢查（AGENTS.md）" % SITE_NAME)
    print("檢查了 %d 個主題頁、%d 個原始資料檔\n" % (pages_checked, raw_checked))
    for line in report.errors:
        print("[錯誤] " + line)
    for line in report.warnings:
        print("[警告] " + line)
    if report.errors or report.warnings:
        print()
    print("結果：%d 個錯誤、%d 個警告" % (len(report.errors), len(report.warnings)))
    failed = bool(report.errors) or (strict and bool(report.warnings))
    print("未通過，請依上面的訊息修正。" if failed else "通過。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
