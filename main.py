import os
import requests
import pandas as pd
from datetime import datetime
from data_fetcher import get_bist_tickers, get_takas_data
from quant_engine import (
    calculate_hhi,
    calculate_quant_scores,
    gecmis_veriyi_yukle,
    GECMIS_DOSYA,
)
 
 
def run_pipeline():
    print("1. BIST Verileri Cekiliyor...")
    df = get_bist_tickers()
    if df.empty:
        print("Veri alinamadi, islem iptal.")
        return
 
    print("2. Takas/HHI Verisi Toplaniyor...")
    hhi_list = []
    for ticker in df['ticker']:
        shares = get_takas_data(ticker)
        hhi_list.append(calculate_hhi(shares))
    df['hhi_score'] = hhi_list
  print("3. Gecmis Veri Yukleniyor ve Nicel Skorlama Calistiriliyor...")
    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)
 
    # Bugunun anlik goruntusu - Streamlit dashboard bunu okur (her gun uzerine yazilir)
    df.to_csv("sonuclar.csv", index=False)
    print("4. 'sonuclar.csv' guncellendi (bugunun anlik goruntusu).")
 
    # ESKI HATA: Bu adim yoktu, sonuclar.csv her gun tamamen uzerine yaziliyordu.
    # Sonuc: gercek RVOL hicbir zaman hesaplanamiyordu, takas yogunlasmasindaki
    # DEGISIM izlenemiyordu, backtest imkansizdi.
    # DUZELTME: Tarihsel kayda EKLE (append) - RVOL/HHI trend hesaplarinin temeli.
    df_bugun_kayit = df[['ticker', 'close', 'volume', 'change_%', 'hhi_score']].copy()
    df_bugun_kayit['tarih'] = datetime.now().strftime('%Y-%m-%d')
    dosya_var_mi = os.path.exists(GECMIS_DOSYA)
    df_bugun_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not dosya_var_mi, index=False)
    print("5. 'gecmis_veri.csv' tarihsel kayit guncellendi (append).")
 
    # Top 3 Telegram'a gonder
    bot_token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
 
    if bot_token and chat_id:
        top_hisseler = df.head(3)
        msg = "\U0001F6A8 *BIST QUANT RADAR TOP SINYALLER*\n\n"
        for _, row in top_hisseler.iterrows():
            uyari = " (yeni/az gecmis)" if row['gecmis_yetersiz'] else ""
            msg += f"\U0001F4CC *#{row['ticker']}*{uyari}\n"
            msg += f"- Quant Skor: {row['quant_score']:.1f}/100\n"
            msg += f"- RVOL (kendi ortalamasina gore): {row['rvol_ratio']:.2f}x\n"
            msg += f"- Takas HHI Yuzdelik Dilimi: %{row['pct_hhi']:.0f}\n"
            msg += f"- Fiyat Degisim: %{row['change_%']:.2f}\n\n"
 
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg})
        print("6. Telegram bildirimi gonderildi.")
 
 
if __name__ == "__main__":
    run_pipeline()
 
