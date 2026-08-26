import requests
import pandas as pd
import numpy as np
import concurrent.futures
from datetime import datetime

def get_bist_tv_data():
    """TradingView üzerinden hacmi en yüksek 250 BIST hissesini OHLCV formatında çeker."""
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "columns": ["name", "close", "high", "low", "volume", "change", "Value.Traded"],
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range": [0, 250]
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.tradingview.com/"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()
        rows = []
        for item in data.get("data", []):
            d = item["d"]
            rows.append({
                "ticker": d[0], 
                "close": float(d[1]) if d[1] is not None else 0.0, 
                "high": float(d[2]) if d[2] is not None else 0.0,
                "low": float(d[3]) if d[3] is not None else 0.0,
                "volume": float(d[4]) if d[4] is not None else 0.0, 
                "change_%": float(d[5]) if d[5] is not None else 0.0, 
                "value_traded": float(d[6]) if d[6] is not None else 0.0
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"TradingView Hatası: {e}")
        return pd.DataFrame()

def fetch_single_takas(ticker):
    """Tek bir hisse için İş Yatırım'dan HHI ve Yabancı Takas çeken kamufle edilmiş işçi fonksiyon"""
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.YatirimDanismanligi/PiyasaVerileri.aspx/GetHisseTakasData"
    
    # Gerçek tarayıcı taklidi (Anti-Bot kamuflajı)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Referer": "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/default.aspx"
    }
    try:
        res = requests.get(url, params={"hisseKodu": ticker}, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json().get("d", [])
            if not data: 
                return ticker, 0.0, 0.0
            
            # HHI Konsantrasyon Skoru
            shares = np.array([float(x.get("Yuzde", 0) or 0) for x in data[:15]])
            hhi = float(np.sum(((shares / shares.sum()) * 100) ** 2)) if shares.sum() > 0 else 0.0
            
            # Yabancı Kurum Payı (Citi, Deutsche, HSBC)
            foreign_banks = ["CITIBANK YABANCI", "DEUTSCHE YABANCI", "HSBC YATIRIM"]
            f_ratio = sum([float(x.get("Yuzde", 0) or 0) for x in data if str(x.get("ALAN_ADI")).upper() in foreign_banks])
            
            return ticker, round(hhi, 2), round(f_ratio, 2)
        else:
            print(f"[{ticker}] İş Yatırım HTTP Yanıtı: {res.status_code}")
            return ticker, 0.0, 0.0
    except Exception as e: 
        print(f"[{ticker}] Bağlantı Hatası: {e}")
        return ticker, 0.0, 0.0

def fetch_all_data():
    """Ana Fonksiyon: Fiyat ve Takas verilerini asenkron (paralel) toplar ve birleştirir."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TradingView üzerinden piyasa verileri çekiliyor...")
    df_market = get_bist_tv_data()
    
    if df_market.empty:
        print("Hata: Piyasa verisi alınamadı.")
        return df_market

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(df_market)} hisse için Takas verileri paralel çekiliyor...")
    
    takas_results = []
    tickers = df_market['ticker'].tolist()
    
    # 20 paralel thread ile saniyeler içinde tamamlama
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_takas, ticker): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(futures):
            takas_results.append(future.result())

    df_takas = pd.DataFrame(takas_results, columns=['ticker', 'hhi_score', 'foreign_ratio'])
    df_final = pd.merge(df_market, df_takas, on='ticker', how='left')
    
    df_final['hhi_score'] = df_final['hhi_score'].fillna(0.0)
    df_final['foreign_ratio'] = df_final['foreign_ratio'].fillna(0.0)
    df_final['tarih'] = pd.Timestamp.now().normalize()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Veri toplama tamamlandı.")
    return df_final

if __name__ == "__main__":
    test_df = fetch_all_data()
    print(test_df.head(10))
