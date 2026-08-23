import requests
import pandas as pd
import numpy as np
import time

def get_bist_tickers():
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "columns": ["name", "close", "volume", "change", "Value.Traded"],
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range": [0, 250]
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()
        rows = []
        for item in data.get("data", []):
            d = item["d"]
            rows.append({
                "ticker": d[0], "close": d[1], "volume": d[2], 
                "change_%": d[3], "value_traded": d[4]
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"TradingView Hatası: {e}")
        return pd.DataFrame()

def get_takas_and_foreign_data(ticker):
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.YatirimDanismanligi/PiyasaVerileri.aspx/GetHisseTakasData"
    headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.isyatirim.com.tr/"}
    try:
        res = requests.get(url, params={"hisseKodu": ticker}, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("d", [])
            if not data: return 0.0, 0.0
            
            # HHI (Konsantrasyon)
            shares = np.array([float(x.get("Yuzde", 0)) for x in data[:15]])
            hhi = float(np.sum(((shares / shares.sum()) * 100) ** 2)) if shares.sum() > 0 else 0.0
            
            # Yabancı Payı (Citi + Deutsche + HSBC)
            foreign_banks = ["CITIBANK YABANCI", "DEUTSCHE YABANCI", "HSBC YATIRIM"]
            f_ratio = sum([float(x.get("Yuzde", 0)) for x in data if x.get("ALAN_ADI") in foreign_banks])
            
            return round(hhi, 2), round(f_ratio, 2)
    except: pass
    return 0.0, 0.0
