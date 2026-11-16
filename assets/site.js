/* =============================================================
   assets/site.js：全站共用程式（頁面本身不寫 script，見 AGENTS.md）
   1. 首頁：依 data/pages.js 產生分類目錄，並提供搜尋
   2. 主題頁：依清單順序產生「上一篇／下一篇」
   3. 放在 GitHub Pages 時：把 AGENTS.md、raw/ 等原始檔連結改到 GitHub 原始碼頁
   ============================================================= */
(function () {
  "use strict";

  var pages = window.APO_PAGES || [];
  var categories = window.APO_CATEGORIES || [];
  var current = document.body.getAttribute("data-page") || "";
  var isHome = current === "index";

  function pageHref(slug) {
    return (isHome ? "wiki/" : "") + slug + ".html";
  }

  function make(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---------- 首頁：分類目錄 ---------- */
  function renderCatalog() {
    var box = document.getElementById("catalog");
    if (!box) return;
    box.textContent = "";

    categories.forEach(function (cat) {
      var section = make("section", "category");
      section.id = "cat-" + cat.id;
      section.appendChild(make("h3", "", cat.name));
      section.appendChild(make("p", "category__desc", cat.desc));

      var list = make("ul", "toc");
      var items = pages.filter(function (p) { return p.category === cat.id; });
      items.forEach(function (p) {
        var li = make("li");
        var link = make("a", "", p.title);
        link.href = pageHref(p.slug);
        li.appendChild(link);
        li.appendChild(make("span", "toc__summary", p.summary));
        li.setAttribute("data-search",
          [p.title, p.summary, cat.name].concat(p.keywords || []).join(" ").toLowerCase());
        list.appendChild(li);
      });
      if (!items.length) {
        list.appendChild(make("li", "toc__empty", "這個分類還沒有頁面。"));
      }
      section.appendChild(list);
      box.appendChild(section);
    });

    // 從主題頁的麵包屑點「分類」回來時，捲到那個分類
    if (location.hash.indexOf("#cat-") === 0) {
      var target = document.getElementById(location.hash.slice(1));
      if (target) target.scrollIntoView();
    }
  }

  /* ---------- 首頁：搜尋（多個詞用空白隔開，全部符合才顯示） ---------- */
  function setupSearch() {
    var input = document.getElementById("search");
    var status = document.getElementById("search-status");
    if (!input || !status) return;

    input.addEventListener("input", function () {
      var raw = input.value.trim();
      var terms = raw.toLowerCase().split(/\s+/).filter(Boolean);
      var shown = 0;

      document.querySelectorAll("#catalog .category").forEach(function (section) {
        var visible = 0;
        section.querySelectorAll("li[data-search]").forEach(function (li) {
          var text = li.getAttribute("data-search");
          var hit = terms.every(function (t) { return text.indexOf(t) !== -1; });
          li.hidden = !hit;
          if (hit) visible += 1;
        });
        section.hidden = terms.length > 0 && visible === 0;
        shown += visible;
      });

      if (!terms.length) {
        status.textContent = "";
      } else if (shown) {
        status.textContent = "找到 " + shown + " 頁。";
      } else {
        status.textContent = "沒有找到「" + raw + "」。試試「警戒」「擋土牆」「救助」，或直接看下面的目錄。";
      }
    });
  }

  /* ---------- 主題頁：上一篇／下一篇 ---------- */
  function pagerLink(page, label, className) {
    var link = make("a", className);
    link.href = pageHref(page.slug);
    link.appendChild(make("span", "pager__label", label));
    link.appendChild(make("span", "pager__title", page.title));
    return link;
  }

  function renderPager() {
    var nav = document.querySelector(".pager");
    if (!nav) return;
    var index = -1;
    pages.forEach(function (p, i) { if (p.slug === current) index = i; });
    if (index < 0) return;
    if (pages[index - 1]) nav.appendChild(pagerLink(pages[index - 1], "上一篇", "pager__prev"));
    if (pages[index + 1]) nav.appendChild(pagerLink(pages[index + 1], "下一篇", "pager__next"));
  }

  /* ---------- 在 GitHub Pages 上：原始檔連結改到 GitHub ---------- */
  function linkSourceFilesToGitHub() {
    var match = location.hostname.match(/^([a-z0-9-]+)\.github\.io$/i);
    if (!match) return; // 本機預覽時保持相對路徑
    var root = new URL(isHome ? "./" : "../", location.href).pathname; // 例：/apo-hillside-wiki/
    var parts = root.split("/").filter(Boolean);
    var repo = parts.length ? parts[0] : match[1] + ".github.io";
    var base = "https://github.com/" + match[1] + "/" + repo + "/blob/main/";

    document.querySelectorAll("a.raw, a[data-source-file]").forEach(function (link) {
      var path = new URL(link.getAttribute("href"), location.href).pathname;
      if (path.indexOf(root) === 0) link.href = base + path.slice(root.length);
    });
  }

  if (isHome) {
    renderCatalog();
    setupSearch();
  } else {
    renderPager();
  }
  linkSourceFilesToGitHub();
})();
