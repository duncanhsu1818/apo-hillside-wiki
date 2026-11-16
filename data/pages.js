// data/pages.js：全站頁面清單（首頁目錄、搜尋、上一篇／下一篇都從這裡產生）
// 規則見 AGENTS.md 4.1：陣列內容必須是合法 JSON；陣列順序＝閱讀順序，同分類放在一起。
// 新增頁面請用：python3 scripts/new_page.py <slug> --title ... --category ... --summary ...

window.APO_CATEGORIES = [
  {"id": "basics", "name": "認識山坡地", "desc": "山坡地怎麼定義、坡度怎麼分級。"},
  {"id": "rain", "name": "大雨警戒", "desc": "土石流警戒燈號、前兆，以及什麼時候該離開。"},
  {"id": "home", "name": "住的安全", "desc": "哪些山坡地不能蓋房子、房子和擋土牆要隔多遠。"},
  {"id": "aid", "name": "災後協助", "desc": "受災以後可以申請的救助與流程。"}
];

window.APO_PAGES = [
  {"slug": "what-is-slopeland", "title": "怎樣才算山坡地？", "category": "basics", "summary": "標高 100 公尺以上，或平均坡度 5% 以上的土地，經政府劃定並報行政院核定公告，才是法律上的山坡地。", "keywords": ["山坡地", "坡度", "標高", "水土保持法", "坡度分級"], "updated": "2026-11-14"},
  {"slug": "debris-flow-alerts", "title": "土石流黃色、紅色警戒差在哪？", "category": "rain", "summary": "黃色警戒看預測雨量、紅色警戒看實際降雨；黃色時地方政府勸告疏散，紅色時會勸告或強制撤離。", "keywords": ["黃色警戒", "紅色警戒", "警戒基準值", "撤離", "災害防救法"], "updated": "2026-11-14"},
  {"slug": "debris-flow-signs", "title": "土石流要來之前，有哪些前兆？", "category": "rain", "summary": "溪水突然變混濁、流量暴增或驟減、山裡傳出異常聲響，都是土石流前兆；發現了就往溪流兩側高處走。", "keywords": ["前兆", "徵兆", "溪水混濁", "避難", "逃生"], "updated": "2026-11-14"},
  {"slug": "no-build-slopes", "title": "哪些山坡地不能蓋房子？", "category": "home", "summary": "平均坡度超過 30%、順向坡有滑動之虞、靠近活動斷層或斷崖等 8 種情形，依法不得開發建築。", "keywords": ["不得開發建築", "順向坡", "活動斷層", "斷崖", "建築技術規則"], "updated": "2026-11-14"},
  {"slug": "retaining-wall-distance", "title": "房子要離擋土牆多遠？", "category": "home", "summary": "擋土設施高 1.5 公尺以上，房子外牆至少離 2 公尺；擋土設施高 3.6 公尺以上，距離要依公式再加大。", "keywords": ["擋土牆", "擋土設施", "退縮距離", "建築技術規則"], "updated": "2026-11-14"},
  {"slug": "debris-flow-relief", "title": "土石流受災後，可以申請哪些救助？", "category": "aid", "summary": "死亡或失蹤每人 20 萬元、重傷 10 萬元，住屋毀損到不堪居住每人 2 萬元、最多 5 人，由縣市政府發給。", "keywords": ["災害救助", "安遷救助", "救助金", "不堪居住", "大規模崩塌"], "updated": "2026-11-14"}
];
