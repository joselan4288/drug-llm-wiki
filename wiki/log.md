---
id: log
title: Wiki 操作紀錄
type: log
sources: []
related: [index]
---

# Wiki 操作紀錄

依時間記錄每一次 ingest／compile／lint／query。詳細的輸出見 `logs/`。

## 2026-11-17

- **討論**：與作者確認簡報主題（自律神經藥物入門）、Wiki 粒度（概念頁＋類別頁）、存放位置（新 repo）。
- **ingest**：從 Claude Docs《臺灣常用藥物講義》匯入 12 個分頁 → `raw/01`～`raw/12`。
- **compile**：產生 83 個類別頁、3 個彙整頁（藥名索引、字尾總表、情境總表）。
  - 修正：中文緊貼英文的藥名（如「Scopolamine東莨菪鹼」）抓不到 → 改用只看英文字母的邊界。
  - 修正：商品名（Aldactone 等）被當成藥名 → 只出現在「臺灣商品名」欄的字排除。仍有少數商品名寫在「代表藥」或「逆轉劑」欄（如 Bridion、Asacol）會混入索引，列為已知限制。
- **撰寫**：13 個概念頁（自律神經為主，另有血鉀、過敏性休克等跨篇頁）。
- **lint**：第 1 輪 9 個錯誤（frontmatter 漏列來源 5 個、段落缺來源 4 個）→ 第 2 輪 1 個 → 第 3 輪 0 個。
- **自我修正**：撰寫時把「抗組織胺與類固醇不能取代 Epinephrine」標成〔10-immunology#五〕，實際出自〔10-immunology#十二〕，已改正；並把自己補充的機轉解釋改標為「推理（非來源原文）」。

## 來源問題（不改 raw，只在此記錄）

| 位置 | 問題 | Wiki 的處理 |
| --- | --- | --- |
| 〔01-autonomic#二〕 | 「直接促效劑假扣 ACh」應為「假扮」 | 概念頁未引用此句 |
| 〔01-autonomic#四〕 | Dantrolene 的中文名寫作「單挫林」，與常見譯名不同 | 概念頁只寫學名 Dantrolene |
| 〔07-respiratory〕與〔01-autonomic〕 | 前者用「致效劑」，後者用「促效劑」，同一概念兩種譯名 | 概念頁統一用「促效劑」 |
| 〔06-gastrointestinal#一〕〔08-urinary#一〕 | 原講義的互動圖無法轉成文字 | raw 中以佔位文字標示 |
