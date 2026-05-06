本文件是策略產品說明書， 這是用途是給人、Codex、VS Code 專案作為產品與策略規格依據。

# Current Codex Handoff

這一段是給下次新對話接續用的目前實作摘要。

## 目前策略方向

目前程式已從原本的「箱型高點突破追價」改成「第三波推動浪起漲點」偵測。

目前不是嚴格完整 Elliott Wave 自動數浪系統，而是 pivot-based Wave3 setup：

- 找 L1 -> H1 -> L2
- L1 是第一波起點低點
- H1 是第一波高點
- L2 是第二波回檔低點
- L2 必須高於 L1，代表第二波沒有破第一波起點
- L2 後價格重新轉強，視為第三波可能起漲
- 仍需要 HTF / MTF 多頭與成交量條件配合

## Buy3 定義

Buy3 目前由 `StructureDetector.detect_wave3_setup_ltf()` 產生，再由 `StrategyEngine.generate_signals()` 過濾。

Buy3 條件：

- HTF trend 為多頭
- MTF trend 為多頭
- LTF 出現 Wave3 setup
- volume condition 成立
- 每段 Wave2 setup 只取第一個 Buy3，出場後可繼續尋找下一段 setup

策略模式：

- `Legacy Box Breakout`：箱型突破模式，使用原先 breakout / HL / EMA / volume 條件，並支援連續交易
- `Original Wave3`：保留 Wave3 行為，不套用額外品質門檻
- `Quality Filtered`：實驗模式，加入第一版品質過濾，方便逐檔比較

Legacy Box Breakout 條件：

- HTF trend 為多頭
- MTF trend 為多頭
- MTF higher low 成立
- LTF box breakout 成立
- LTF close above EMA
- volume condition 成立
- 空手時才進場；TP/SL 出場後可繼續尋找下一筆

Legacy Box Breakout 出場：

```text
entry_price = LTF Close
stop_loss = entry_price * (1 - STOP_LOSS_PCT)
take_profit = entry_price + (entry_price - stop_loss) * LEGACY_BOX_TARGET_R_MULTIPLE
```

Quality Filtered 條件：

- Buy3 收盤價必須突破或接近 H1：`Close >= H1 * (1 - WAVE3_BREAKOUT_TOLERANCE_PCT)`
- 風報比必須達標：`risk_reward >= WAVE3_MIN_RISK_REWARD`
- 預期漲幅必須達標：`expected_gain_pct >= WAVE3_MIN_EXPECTED_GAIN_PCT`

目前預設：

- `STRATEGY_MODE = "wave3"` in config；Streamlit sidebar 預設顯示 `Legacy Box Breakout` 方便比較舊策略
- `LEGACY_BOX_TARGET_R_MULTIPLE = 2.0`
- `WAVE3_USE_QUALITY_FILTERS = False`
- `WAVE3_BREAKOUT_TOLERANCE_PCT = 0.005`
- `WAVE3_MIN_RISK_REWARD = 1.5`
- `WAVE3_MIN_EXPECTED_GAIN_PCT = 2.0`

圖上的 `Buy3 (price)`：

- marker 標在哪根 K 棒下方，那根 K 棒就是 Buy3 K 棒
- 括號裡的 price 是該根 Buy3 K 棒的收盤價，也就是 `entry_price`

## 停損停利

目前停損停利公式：

```text
wave1_length = H1 - L1
stop_loss = L2 * (1 - WAVE3_STOP_BUFFER_PCT)
take_profit = L2 + wave1_length * WAVE3_TARGET_EXTENSION
```

目前參數在 `src/mteb_v1/config.py`：

- `WAVE3_REBOUND_LOOKBACK = 3`
- `WAVE3_TARGET_EXTENSION = 1.618`
- `WAVE3_STOP_BUFFER_PCT = 0.005`
- `LEGACY_BOX_TARGET_R_MULTIPLE = 2.0`
- `WAVE3_USE_QUALITY_FILTERS = False`
- `WAVE3_BREAKOUT_TOLERANCE_PCT = 0.005`
- `WAVE3_MIN_RISK_REWARD = 1.5`
- `WAVE3_MIN_EXPECTED_GAIN_PCT = 2.0`

圖上：

- 紅色水平虛線是 stop loss
- 綠色水平虛線是 take profit
- 停損 / 停利圖層目前取最新一筆 Buy3 的水平價格，從 Buy3 K 棒延伸到最新 K 棒
- 圖表同時打開 Lightweight Charts 的 `priceLineVisible`，即使線段很短或 Buy3 靠近右側，也會顯示整張圖可見的水平價位線
- 若 Buy3 後 `Low <= stop_loss`，出場原因是 `SL`
- 若 Buy3 後 `High >= take_profit`，出場原因是 `TP`
- 策略目前支援多筆交易循環：空手找 Buy3、持倉等 TP/SL、出場後繼續找下一筆
- 圖表會標示出場 marker：`TP (price)` 或 `SL (price)`
- Streamlit 會顯示 Trade History，將每筆 Entry / Exit 成對列出，勝率統計以這些完成交易為基礎

## 2026-05-05 bug 記錄：2330 停損停利線與刷新 Symbol

### 病因

1. `Symbol` sidebar input 原本使用固定預設 `value="AAPL"`。Streamlit 按鈕、重新整理、widget rerun 都會重新執行 script；若 Symbol 沒有被明確綁到 `st.session_state` 或 URL query param，就容易回到 AAPL。
2. 停損 / 停利線原本只用第一筆 entry 的 level，並延伸到第一個 exit。對 2330.TW 這種已經大幅走過 Buy3 的資料，線段可能很短、位置偏左，甚至被 hover-card 或可視比例影響，看起來像沒有停損停利線。

### 修法

1. `app/streamlit_app.py` 將 Symbol 改成 `key="symbol_input"`，並同步到 `st.query_params["symbol"]`。刷新頁面會從 URL query param 還原 Symbol，因此 `2330` 不會自動跳回 AAPL。
2. `src/mteb_v1/streamlit_charts.py::signal_level_to_line()` 改成取最新一筆 Buy3 的 `stop_loss` / `take_profit`，並延伸到最新 K 棒。
3. `app/streamlit_app.py` 的 stop / target line series 開啟 `priceLineVisible`，讓紅色停損、綠色停利水平價位即使在特殊縮放下仍可見。

### 驗證

測試必須使用專案 `.venv`：

```bash
.venv/bin/python -m pytest tests/test_strategy.py tests/test_structure.py tests/test_streamlit_charts.py
```

2026-05-05 結果：`23 passed in 10.16s`。

## UI 目前狀態

Streamlit app：

- 主要檔案是 `app/streamlit_app.py`
- cursor hover 顯示 Open / Close / Volume / Upper wick / Lower wick
- hover-card 有 `pointer-events: none`，避免擋住滑鼠 crosshair
- Latest 表格顯示 Entry / Stop / Target / Expected Gain / R/R / Exit / Last Buy3
- Latest metrics 顯示 Entries / Closed / Open / Wins / Losses / Win Rate；勝率只用 Closed 交易計算
- Trade History 表格顯示 Entry Time / Entry Price / Stop / Target / Exit Time / Exit Price / Result
- 因為 Streamlit 熱重載可能留住舊 module，app 目前會 reload `config` / `streamlit_charts` / `structure` / `strategy`
- Symbol 會同步到 session state 與 URL query param，重新整理後保留目前標的

## 測試方式

本專案虛擬環境在 `.venv`。

跑測試請用：

```bash
.venv/bin/python -m pytest
```

最近一次相關測試：

```bash
.venv/bin/python -m pytest tests/test_strategy.py tests/test_streamlit_charts.py tests/test_structure.py tests/test_backtest.py
```

結果是 35 passed。

## 後續想做

下一步希望加入 Buy3 評分制，目前尚未實作。

建議 100 分制：

- 趨勢分：HTF / MTF 多頭
- 波型分：L1-H1-L2 結構品質
- Fibonacci 分：L2 回檔比例、Wave3 extension 合理性
- 成交量分：是否明顯放量
- 風報比分：R/R 是否足夠

可考慮：

- Score >= 75 顯示 Buy3
- Score 60-74 顯示 Watch3
- Score < 60 不顯示訊號

# Contents
1. 策略定位
2. 策略名稱
3. 核心交易邏輯
4. 三時框定義
5. 市場狀態判斷
6. 進場邏輯
7. 出場邏輯
8. 風控邏輯
9. 使用者介面設計
10. 圖表顯示元素
11. 參數面板
12. 狀態面板
13. 交易標籤
14. 報表輸出
15. 使用流程
16. 限制與風險

# User Interface
圖表主區：
- K線
- 波浪線
- H/L 節點
- BUY-3 標籤
- SL / Trail 線
- EXIT 標籤

右上狀態面板：
- HTF 狀態
- MTF 狀態
- HL 是否成立
- 箱體突破狀態
- 量能狀態
- 鎖定狀態
- 持倉狀態

# 📊 MTEB-V4 策略說明書
Multi-Timeframe Trend Expansion Breakout Strategy

中文名稱：
三時框主升段突破交易策略

---

# 1️⃣ 策略定位

本策略是一套：

- 低頻交易
- 高勝率
- 趨勢追蹤（Trend Following）
- 結構驅動（Structure-based）

的交易系統。

核心目標：

> 只交易「盤整 → 突破 → 主升段」的行情  
> 並透過移動停利持有最大波段利潤

---

# 2️⃣ 核心理念

市場大部分時間不可交易  
只在「結構完成 + 突破成立」時進場

---
不是找波浪  
而是找「最有力量的趨勢段」

---

---
進場決定是否能賺  
出場決定能賺多少

---

# 3️⃣ 三時框架構（Multi-Timeframe）

| 層級 | 時框 | 功能 |
|------|------|------|
| HTF | 日K | 判斷方向 |
| MTF | 1H  | 判斷結構 |
| LTF | 15m | 進場與風控 |

---

## 三時框本質

方向（HTF）  
↓  
結構（MTF）  
↓  
進場（LTF）

---

# 4️⃣ 市場狀態分類

## 🟢 趨勢市場（可交易）

特徵：

- Higher High / Higher Low
- 突破後不回頭
- 回檔淺

---

## 🔴 盤整市場（禁止交易）

特徵：

- 高低點混亂
- 多次假突破
- 成交量不穩

---

# 5️⃣ 結構定義（Structure）

## Pivot（轉折點）

市場的「確認高點 / 低點」

---

## Higher Low（HL）

後一個低點 > 前一個低點

代表：

→ 多頭結構成立

---

## 結構成立條件
必須出現 HL

---

# 6️⃣ 箱體（盤整區）

## 定義

過去一段時間內：

- 價格在區間震盪
- 未形成趨勢

---

## 箱體高點
區間內最高價

---

## 箱體意義
突破箱體 = 主升段開始

---

# 7️⃣ 進場邏輯（Entry）

## 必須同時成立：

---

### 1️⃣ 趨勢方向

- HTF 為多頭
- MTF 為多頭

---

### 2️⃣ 結構成立

- 出現 Higher Low（HL）

---

### 3️⃣ 突破成立

- 價格突破箱體高點

---

### 4️⃣ 突破強度

- 不是假突破
- 有動能

---

### 5️⃣ 成交量條件

- 突破時有量

---

### 6️⃣ 趨勢過濾

- 價格在 EMA 上方

---

### 7️⃣ 不追高

- 不在已經過度延伸的位置進場

---

### 8️⃣ 單次進場

- 每段趨勢只進場一次

---

## 🎯 進場結果
BUY-3（主升段進場）

---

# 8️⃣ 出場邏輯（Exit）

---

## 1️⃣ 停損（SL）

- 防止重大虧損

---

## 2️⃣ 移動停利（TRAIL）

- 隨價格上升
- 鎖住利潤

---

## 3️⃣ 結構破壞

- 跌破關鍵低點（HL）

---

## 4️⃣ 趨勢失效

- HTF 或 MTF 轉弱

---

## 🎯 出場原則
不是預測高點  
而是讓市場告訴你什麼時候結束

---

# 9️⃣ 風控系統（Risk Management）

| 類型 | 功能 |
|------|------|
| SL | 控制虧損 |
| TRAIL | 保護利潤 |
| 結構出場 | 避免趨勢反轉 |
| 趨勢出場 | 避免逆勢 |

---

# 🔟 單次進場機制（Cycle Lock）

## 鎖定

進場後：

→ 不允許再次進場

---

## 解鎖條件

- 趨勢結束
- 結構破壞
- 新結構形成

---

# 11️⃣ 使用者介面（TradingView風格）

---

## 📊 主圖顯示

---

### K線

- 價格主體

---

### 波浪線（黃色）

- 連接高低點
- 顯示市場結構

---

### Pivot 標記

- H（高點）
- L（低點）

---

### BUY 標籤

- BUY-3
- 顯示進場位置與價格

---

### EXIT 標籤

- SL / TRAIL / STRUCT / TREND

---

### 風控線

| 顏色 | 意義 |
|------|------|
| 灰色 | Entry |
| 紅色 | Stop Loss |
| 藍色 | Trail |

---

## 📈 視覺邏輯
價格上漲 → TRAIL 上移  
價格跌破 → 出場

---

# 12️⃣ 狀態面板（右上角）

---

| 項目 | 說明 |
|------|------|
| HTF/MTF | 是否多頭 |
| HL | 結構是否成立 |
| Breakout | 是否突破 |
| Volume | 量能是否成立 |
| Lock | 是否鎖定 |
| Position | 是否持倉 |
| Status | BUY / EXIT / WAIT |

---

# 13️⃣ 交易標籤

---

## BUY
BUY-3  
價格

---

## EXIT
SL  
TRAIL  
STRUCT EXIT  
TREND EXIT

---

# 14️⃣ 使用流程

---

## Step 1

觀察 HTF / MTF 是否多頭

---

## Step 2

等待 HL 出現

---

## Step 3

等待突破箱體

---

## Step 4

確認不是追高

---

## Step 5

進場 BUY-3

---

## Step 6

使用 TRAIL 持有

---

## Step 7

等待出場訊號

---

# 15️⃣ 策略特性

---
✔ 訊號少  
✔ 精準  
✔ 可持續優化  
✔ 可量化  
✔ 可自動化

---

# 16️⃣ 限制與風險

---

## ❗ 盤整期

- 訊號可能失效

---

## ❗ 延遲

- Pivot 為確認訊號

---

## ❗ 漏掉行情

- 過濾嚴格 → 可能錯過部分上漲

---

## ❗ 非預測系統

- 不預測未來
- 只反應結構

---

# 🚀 核心總結
盤整 → 突破 → 主升段 → 持有 → 結束

---

# 👍 最重要一句
我們不是在找完美波浪  
而是在找可重複賺錢的結構
