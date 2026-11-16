# 阿坡伯山坡地小百科

用白話整理「山坡地安全」的小網站：怎樣算山坡地、土石流黃色和紅色警戒差在哪、哪些山坡地不能蓋房子、受災後可以申請什麼。每一頁都附上法規或官方資料的原文出處。

- 網站：https://duncanhsu1818.github.io/apo-hillside-wiki/
- 原始碼：https://github.com/duncanhsu1818/apo-hillside-wiki
- 專案規則：[AGENTS.md](AGENTS.md)

## 這個專案的重點：先寫規則，再讓 AI 照規則做頁面

| 檔案 | 角色 |
|---|---|
| `AGENTS.md` | 規則：專案目的、網頁風格、頁面結構、內容格式、命名與放置、AI 必須遵守的事 |
| `CLAUDE.md` | 給 Claude Code 的入口，只匯入 AGENTS.md，所有 AI 讀同一份規則 |
| `templates/page.html` | 格式：每個主題頁都用同一個骨架 |
| `scripts/new_page.py` | 快速建頁：一行指令產生新頁，並登記到 `data/pages.js` |
| `scripts/check_site.py` | 檢查：區塊順序、出處、連結、命名是否符合規則 |
| `raw/` | 依據：法規與官方資料原文（唯讀） |
| `log.md` | 紀錄：每次新增或修改了什麼、為什麼 |

## 本機預覽

不用安裝任何東西，直接用瀏覽器打開 `index.html` 就能看。

## 新增一頁

```bash
python3 scripts/new_page.py retaining-wall-drains \
  --title "擋土牆排水孔不出水，怎麼辦？" --category home \
  --summary "（一句話給答案，20～60 字）" --keywords "擋土牆,排水孔"
# 依 AGENTS.md 填完內容後檢查
python3 scripts/check_site.py
```

也可以直接對 AI 說：「照 AGENTS.md 新增一頁：……」。Windows 若沒有 `python3` 指令，改打 `python`。

## 發佈到 GitHub Pages

1. 在 GitHub 建立公開的 repository，名稱建議 `apo-hillside-wiki`。
2. 上傳這個資料夾裡的全部檔案（包含 `.nojekyll`）。
3. 到 repository 的 **Settings → Pages**，Source 選 **Deploy from a branch**，Branch 選 **main**、資料夾選 **/(root)**，按 **Save**。
4. 等一兩分鐘，同一頁上方會出現網站網址。

## 資料來源與聲明

- 法規條文來自全國法規資料庫；土石流警戒與避難說明來自農業部農村發展及水土保持署「土石流及大規模崩塌防災資訊網」。每一頁的「資料來源」都有官方網址與對應的 `raw/` 檔。
- 本站是課程作業與知識整理，不是即時警報。遇到危險請先離開、撥打 119，並依地方政府指示撤離。

## AI 協作說明

本專案在 AI（Anthropic 的 Claude）協助下完成：AI 依作者指定的主題撰寫 AGENTS.md 草稿、網站程式與主題頁，每一頁都依 AGENTS.md 製作，並通過 `scripts/check_site.py` 檢查。所有變更紀錄見 `log.md`。
