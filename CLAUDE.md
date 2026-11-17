# CLAUDE.md — 臺灣常用藥物 LLM Wiki

> 這份文件是 Wiki 的 **schema**：告訴 AI 這個知識庫怎麼分層、頁面長什麼樣子、
> 新資料進來時要怎麼 ingest、回答問題或做簡報時要怎麼 query、以及怎麼 lint。
> 任何修改前請先完整讀完。`AGENTS.md` 只是指向本文件。

---

## 1. 目的

把作者自己整理的《臺灣常用藥物講義》（12 個分頁）編譯成一個**互相連結、可查詢、可檢查**的 Wiki，
再以 Wiki 作為唯一知識來源，產生給初學者的教學 HTML 簡報。

- 讀者：完全不熟藥理、但想理解「藥為什麼有這些作用與副作用」的人。
- 原則：**Wiki 只寫來源裡有的東西**。來源沒有的事實不寫；需要補充時先 ingest 新來源。

## 2. 三層架構

| 層 | 資料夾 | 誰寫 | 可否修改 |
| --- | --- | --- | --- |
| 原始資料 | `raw/` | `scripts/ingest_docs.py` 從 Claude Docs 匯入 | **不可手改**；要更新就重新 ingest |
| Wiki | `wiki/` | `scripts/compile_wiki.py`（類別頁、彙整頁）＋ AI 撰寫（概念頁） | 可以，但每次修改都要記在 `wiki/log.md` |
| 產出 | `slides/` | AI 依 Wiki 產生 | 可以，必須通過 `scripts/check_slides.py` |

## 3. 頁面類型

每個 Wiki 頁是 `wiki/<id>.md`，開頭有 YAML frontmatter：

```yaml
---
id: concept-beta-receptor        # 與檔名相同，英文小寫＋連字號
title: β 受體
type: concept                    # concept | class | aggregate | index | log
sources: [01-autonomic#一, 02-cardiovascular#一]   # raw 檔名#H2 編號
related: [class-01-07, concept-alpha-receptor]
---
```

| type | 前綴 | 內容 | 產生方式 |
| --- | --- | --- | --- |
| `class` 藥物類別頁 | `class-<raw編號>-<H2序號>` | 一個 H2 章節的藥物表格與說明，原文照搬並加上來源與相關連結 | 腳本 |
| `concept` 概念頁 | `concept-<英文名>` | 跨章節的觀念（受體、副作用機轉、中毒處置等），用自己的話整理 | AI 撰寫 |
| `aggregate` 彙整頁 | `agg-<英文名>` | 跨 12 篇自動彙整：藥名索引、字尾表、臨床情境總表 | 腳本 |
| `index` / `log` | `index`、`log` | 目錄與操作紀錄 | 腳本／AI |

## 4. 寫作規則

1. **連結**：用 `[[id]]` 或 `[[id|顯示文字]]`。連到不存在的頁面視為錯誤。
2. **來源**：概念頁每一段事實後面標 `〔01-autonomic#一〕`（raw 檔名＋H2 中文序號）。沒有來源標記的段落視為錯誤。
3. **不改寫數字**：劑量、時間、百分比必須與來源完全一致；有疑慮就照抄來源原句。
4. **商品名**：只用來源中出現過的臺灣商品名，不可自行補。
5. **繁體中文、臺灣用語**；學名用英文。
6. 發現來源本身有錯字或可疑處：Wiki 照正確寫法，並在 `wiki/log.md` 的「來源問題」記一筆，**不改 raw**。

## 5. 三個操作

### ingest（新增或更新來源）
1. 讀取 Claude Docs 分頁 → `scripts/ingest_docs.py` → `raw/NN-slug.md`
2. `python3 scripts/compile_wiki.py` 重新產生類別頁與彙整頁
3. 檢查受影響的概念頁是否需要更新，更新後在 `log.md` 記一筆

### query（回答問題或做簡報）
1. 先讀 `wiki/index.md` 找相關頁，再讀頁面本身；**不要直接讀 raw**
2. 回答或投影片內容只能來自讀到的頁面；每張投影片在 `data-cite` 列出引用的頁面 id
3. Wiki 缺資料時，回到 ingest，而不是自己補

### lint（檢查）
- `python3 scripts/lint_wiki.py`：斷連結、孤兒頁、缺來源標記、來源標記指向不存在的章節、簡體字
- `python3 scripts/check_slides.py`：投影片裡的藥名、商品名、數字是否都出現在 `data-cite` 引用的頁面中

## 6. 檔案結構

```
drug-llm-wiki/
├── CLAUDE.md / AGENTS.md     ← 本文件（schema）
├── README.md                 ← 專案說明、loop/graph 設計
├── index.html                ← 網站首頁
├── wiki.html                 ← Wiki 瀏覽器（讀 wiki/*.md）
├── raw/                      ← 12 篇原始講義（不可手改）
├── wiki/                     ← Wiki 頁面、index.md、log.md
├── slides/index.html         ← 教學 HTML 簡報
├── scripts/                  ← ingest / compile / lint / check
├── logs/                     ← 每次實際執行的檢查紀錄
└── assets/vendor/marked.min.js
```
