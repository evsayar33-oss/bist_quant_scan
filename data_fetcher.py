import requests
import pandas as pd
import numpy as np
import concurrent.futures
import time
from datetime import datetime

def get_bist_tv_data():
    """TradingView üzerinden hacmi en yüksek 250 BIST hissesini OHLCV formatında çeker."""
    url = "https://scanner.tradingview.com/turkey/scan"
    # DİKKAT: Kurumsal CLV mikroyapısı için 'high' ve 'low' sütunları eklendi.
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "columns": ["name", "close", "high", "low", "volume", "change", "Value.Traded"],
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
                "ticker": d[0], 
                "close": float(d[1]) if d[1] else 0.0, 
                "high": float(d[2]) if d[2] else 0.0,
                "low": float(d[3]) if d[3] else 0.0,
                "volume": float(d[4]) if d[4] else 0.0, 
                "change_%": float(d[5]) if d[5] else 0.0, 
                "value_traded": float(d[6]) if d[6] else 0.0
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"TradingView Hatası: {e}")
        return pd.DataFrame()

def fetch_single_takas(ticker):
    """Tek bir hisse için İş Yatırım'dan HHI ve Yabancı Takas çeken işçi (worker) fonksiyon"""
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.YatirimDanismanligi/PiyasaVerileri.aspx/GetHisseTakasData"
    headers = {
        "User-Agent": "Mozilla/5.0", 
        "X-Requested-With": "XMLHttpRequest", 
        "Referer": "https://www.isyatirim.com.tr/"
    }
    try:
        res = requests.get(url, params={"hisseKodu": ticker}, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("d", [])
            if not data: 
                return ticker, 0.0, 0.0
            
            # HHI (Konsantrasyon)
            shares = np.array([float(x.get("Yuzde", 0) or 0) for x in data[:15]])
            hhi = float(np.sum(((shares / shares.sum()) * 100) ** 2)) if shares.sum() > 0 else 0.0
            
            # Yabancı Payı (Citi + Deutsche + HSBC)
            foreign_banks = ["CITIBANK YABANCI", "DEUTSCHE YABANCI", "HSBC YATIRIM"]
            f_ratio = sum([float(x.get("Yuzde", 0) or 0) for x in data if str(x.get("ALAN_ADI")).upper() in foreign_banks])
            
            return ticker, round(hhi, 2), round(f_ratio, 2)
    except: 
        pass
    return ticker, 0.0, 0.0

def fetch_all_data():
    """Ana Fonksiyon: Fiyatları ve Takas verilerini Threading ile hızlıca birleştirir."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TradingView'dan piyasa verileri çekiliyor...")
    df_market = get_bist_tv_data()
    
    if df_market.empty:
        print("Hata: Piyasa verisi alınamadı.")
        return df_market

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(df_market)} hisse için İş Yatırım takas verileri asenkron çekiliyor...")
    
    # Asenkron (Paralel) İstek Havuzu
    takas_results = []
    tickers = df_market['ticker'].tolist()
    
    # Max_workers 20 olarak ayarlandı, ağ trafiğine takılmamak için optimaldir.
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_takas, ticker): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(futures):
            takas_results.append(future.result())

    # Takas sonuçlarını DataFrame'e çevirip ana tabloya (Merge) yediriyoruz
    df_takas = pd.DataFrame(takas_results, columns=['ticker', 'hhi_score', 'foreign_ratio'])
    df_final = pd.merge(df_market, df_takas, on='ticker', how='left')
    
    # Boş kalanları 0 ile doldur
    df_final['hhi_score'] = df_final['hhi_score'].fillna(0.0)
    df_final['foreign_ratio'] = df_final['foreign_ratio'].fillna(0.0)
    df_final['tarih'] = pd.Timestamp.now().normalize()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Veri Toplama Tamamlandı. Motor Başlıyor.")
    return df_final

# Dosya direkt çalıştırılırsa test et:
if __name__ == "__main__":
    test_df = fetch_all_data()
    print(test_df.head(10))
