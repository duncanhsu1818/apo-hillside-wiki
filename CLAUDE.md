# CLAUDE.md

這個專案的規則統一寫在 AGENTS.md，讓 Claude Code、Codex 等工具讀同一份，避免兩份規則越改越不一樣。下面這一行會把 AGENTS.md 整份匯入：

@AGENTS.md

## 給 Claude Code 的補充

- 開工前先跑 `python3 scripts/check_site.py`，確認目前狀態；交付前再跑一次，0 個錯誤才回報完成。
- 新增頁面用 `python3 scripts/new_page.py`，不要複製舊頁面再改。
- 規則要改時改 AGENTS.md（先問使用者），不要把規則寫在這個檔案。
