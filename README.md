# 金門地政雲 (Kinmen Land Cloud Service)

![Version](https://img.shields.io/badge/version-v0.10__20261118-emerald?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Synology%20DS1019%2B%20%7C%20Docker-blue?style=flat-square)
![PostGIS](https://img.shields.io/badge/database-PostgreSQL%2015%20%2B%20PostGIS%203.3-indigo?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-slate?style=flat-square)

> **對標系統**：臺北地政雲 (`fun=g11` 整合資訊查詢系統)  
> **核心架構**：內政部不動產實價登錄動態更新 × 金門都市計畫自然村管制 × 國家公園雙軌管制 × 戰地政務歷史航照捲簾 × 土地農舍合規檢測器  
> **發布版本**：`v0.10_20261118` (2026-11-18)

---

## 🌟 核心特色功能 (Key Features)

1. **整合資訊查詢系統 (fun=g11)**：
   - 涵蓋金門全縣 5 大鄉鎮、250 地段圖資與地號搜尋。
   - 串接中研院 1958/1966 歷史航照圖層與 NLSC 通用地圖。

2. **多維度實價登錄分析**：
   - 即時收錄全島歷季實價交易資料（859+ 筆），支援價格、單價、建物型態、屋齡篩選。
   - 房價熱力圖（Heatmap）與歷季均價走勢分析（ECharts 5.4）。

3. **空間拓樸與建管法規計算**：
   - 金門都市計畫自然村第一至三種建蔽率與容積率試算。
   - 國家公園特別景觀區、史蹟保存區與一般管制區相交判別。
   - 農發條例第 16 條與第 18 條農地分割與農舍興建合規檢測器。

4. **每旬自動同步管線 (Data Pipeline)**：
   - 每月 1、11、21 日 04:00 自動定時爬取內政部地政開放資料庫金門縣專區（代碼 `W`）。

---

## 🚀 部署指引 (Deployment)

詳細部署指引與環境配置請參閱 [DEPLOY.md](DEPLOY.md)。

### Docker Compose 一鍵啟動 (Synology NAS / 伺服器)
```bash
docker compose up -d --build
```
啟動後開啟瀏覽器前往 `http://localhost:8080/` 即可直接使用。

---

## 📌 版本紀錄 (Changelog)

- **`v0.10_20261118`**：
  - 正式發布初始生產版本。
  - 整合 Synology DS1019+ Container Manager 與 GitHub Actions 部署架構。
  - 新增頂部導航列發布版本標籤與系統狀態模態框。
