# Microstructure Data Mining Plan (M1 OHLCV Only)
Version: 1.1  
Status: EXECUTABLE SPEC  
Author: Quant Research Pipeline  

---

# 1. OBJECTIVE

Mengeksplorasi dan memvalidasi edge berbasis **microstructure proxy** dari data M1 OHLCV (XAUUSD, 5 tahun), untuk:

1. Mengidentifikasi pola statistik yang repeatable  
2. Menguji edge secara execution-aware (no look-ahead)  
3. Menghasilkan:
   - Rule-based candidate strategies  
   - Meta-labeling dataset  
   - Feature library reusable  

---

# 2. DATA CONTRACT

## 2.1 Source
- Instrument: XAUUSD  
- Timeframe: M1  
- Duration: ~5 tahun  
- Timezone: UTC+0  

## 2.2 Loader (MANDATORY)

```python
def load_ohlcv(path: str) -> pd.DataFrame:
    names = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
```

## 2.3 Rules
- Skip header row  
- Parse datetime: `%Y.%m.%d %H:%M`  
- Set index: timestamp (UTC)  
- Sort ascending  
- No duplicate index  
- No missing rows (atau flag eksplisit)  

## 2.4 Validation Checks
- Missing bars detection  
- Duplicate timestamp  
- Zero/negative prices  
- Outlier spike detection  

---

# 3. RESEARCH SPLIT (NO LEAKAGE)

Time-based split:

- Train: 60%  
- Validation: 20%  
- Test: 20%  

STRICT RULES:
- No shuffling  
- No future leakage  
- Parameter tuning ONLY on validation  
- Test set digunakan sekali  

Optional:
- Walk-forward validation  

---

# 4. EXECUTION ASSUMPTIONS (CRITICAL)

## 4.1 Entry
- Entry pada next bar open (t+1)

## 4.2 SL / TP
- **SL: structural (swing high / swing low terakhir sebelum entry)**
- **TP: default RR = 1:2**

## 4.3 Timeout
- Max holding: **50 bar**

## 4.4 Intrabar Rule
- Jika SL & TP kena dalam satu bar -> **SL FIRST**

## 4.5 Gap Handling
- Jika gap melewati SL -> fill di harga terburuk (gap stop)

## 4.6 Spread / Cost
- Spread = 0 (baseline)
- Cost modeling ditambahkan di tahap lanjutan

---

# 5. MICROSTRUCTURE PROXY FEATURE LIBRARY

Semua feature HARUS hanya menggunakan data masa lalu.

## 5.1 Candle Anatomy
- range = high - low  
- body = close - open  
- upper_wick  
- lower_wick  
- body_ratio  
- close_position  

## 5.2 Returns
- ret_1, ret_3, ret_5, ret_10  
- cumulative returns rolling  

## 5.3 Volatility
- rolling std (5, 10, 20)  
- ATR proxy  
- compression ratio  

## 5.4 Structure
- rolling high/low  
- distance to high/low  
- breakout distance  
- reversion distance  

## 5.5 Trend Context
- EMA (20, 50)  
- slope EMA  
- distance to EMA  
- BB width  

## 5.6 Momentum / Persistence
- streak up/down  
- directional efficiency  
- clustering  

## 5.7 Session Context
- hour  
- session (Asia / London / NY)  

---

# 6. EVENT DEFINITIONS

## 6.1 Momentum Candle
- body_ratio tinggi  
- break previous high/low  

## 6.2 Sweep + Reclaim
- break rolling high/low  
- close kembali ke dalam range  

## 6.3 Compression -> Expansion
- low volatility window  
- diikuti candle besar  

## 6.4 Inside Bar Breakout
- cluster inside bar  
- breakout close  

## 6.5 Rejection Candle
- wick panjang  
- close berlawanan  

---

# 7. LABELING (TRIPLE BARRIER)

## 7.1 Entry
- Next bar open  

## 7.2 Barrier
- SL: swing terakhir  
- TP: 2R  
- Timeout: 50 bar  

## 7.3 Label
- TP kena dulu -> 1  
- SL kena dulu -> 0  
- Timeout -> optional  

---

# 8. BASELINE STAT MINING

Untuk tiap event:

Hitung:
- total trades  
- winrate  
- avg R  
- profit factor  
- expectancy  

Breakdown:
- per tahun  
- per session  
- per volatility regime  

---

# 9. META-LABELING DATASET

## 9.1 Input
- Feature snapshot saat event

## 9.2 Target
- Triple barrier label

## 9.3 Model
- Logistic Regression  
- XGBoost  

## 9.4 Output
- Probability of success  

## 9.5 Filtering
- Threshold probability  

---

# 10. VALIDATION FRAMEWORK

## 10.1 Required
- Out-of-sample  
- Walk-forward  
- Monte Carlo  

## 10.2 Stability
- Yearly  
- Session  
- Parameter sensitivity  

## 10.3 Metrics
- PF  
- Expectancy  
- Max DD  
- Winrate  
- Trade count  

---

# 11. OUTPUT ARTIFACTS

Mandatory:
- trades.csv  
- metrics.json  
- run_manifest.json  

Optional:
- equity_curve.png  
- monthly_R.csv  
- feature_importance.csv  

---

# 12. SUCCESS CRITERIA

- PF > 1.1 (OOS)  
- Stabil antar tahun  
- Tidak overfit  
- Drawdown terkendali  

---

# 13. FAILURE CONDITIONS

Reject jika:
- PF < 1 (OOS)  
- Tidak stabil  
- Hanya bekerja di 1 regime  
- Sensitif parameter  

---

# 14. NEXT STEPS

1. Feature extraction notebook  
2. Event mining  
3. Baseline stats  
4. Meta-labeling  
5. Validation  

---
