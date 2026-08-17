import requests
import pandas as pd
import time

def get_bist_tickers():
    """TradingView üzerinden BIST verilerini çeker."""
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "columns": ["name", "close", "volume", "change", "Value.Traded"],
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range": [0, 250] # İlk 250 hisse
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()
        rows = []
        for item in data.get("data", []):
            d = item["d"]
            rows.append({
                "ticker": d[0],
                "close": d[1],
                "volume": d[2],
                "change_%": d[3],
                "value_traded": d[4]
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"TradingView Hatası: {e}")
        return pd.DataFrame()

def get_takas_data(ticker):
    """Is Yatirim web servisinden saklama oranlarini ceker."""
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.YatirimDanismanligi/PiyasaVerileri.aspx/GetHisseTakasData"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/default.aspx"
    }
    try:
        params = {"hisseKodu": ticker}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            shares = json_data.get("d", [])
            if shares:
                # Sadece sayısal değerleri çek ve hataları temizle
                return [float(x.get("Yuzde", 0)) for x in shares[:15]]
        # Engellenmemek için kısa bir bekleme (Action hızı için 0.2sn ideal)
        time.sleep(0.2)
    except Exception:
        pass
    return []
