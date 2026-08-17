import os
import requests
import pandas as pd
from datetime import datetime
import pytz
from data_fetcher import get_bist_tickers, get_takas_data
from quant_engine import calculate_hhi, calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def run_pipeline():
    # TR Zaman Dilimi Ayarı
    tr_tz = pytz.timezone('Europe/Istanbul')
    bugun_str = datetime.now(tr_tz).strftime('%Y-%m-%d')
    
    print(f"--- {bugun_str} BIST Quant Taraması Başladı ---")
    
    df = get_bist_tickers()
    if df.empty:
        print("BIST verisi alinamadi.")
        return

    print("Takas verileri toplanıyor...")
    hhi_list = []
    for ticker in df['ticker']:
        shares = get_takas_data(ticker)
        hhi_list.append(calculate_hhi(shares))
    df['hhi_score'] = hhi_list

    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)

    # Günlük sonuç kaydı (Dashboard için)
    df.to_csv("sonuclar.csv", index=False)

    # Geçmiş veri kaydı (Append - RVOL için)
    df_kayit = df[['ticker', 'close', 'volume', 'change_%', 'hhi_score']].copy()
    df_kayit['tarih'] = bugun_str
    
    # Dosya varsa ve bugünün verisi zaten yazılmışsa (tekrar çalıştırma koruması)
    if not df_gecmis.empty:
        if bugun_str in df_gecmis['tarih'].astype(str).values:
            print("Bugünün verisi zaten kayıtlı, üstüne yazılmıyor.")
        else:
            df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=False, index=False)
    else:
        df_kayit.to_csv(GECMIS_DOSYA, index=False)

    # Telegram Bildirimi
    send_telegram_alert(df)

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        top = df.head(5)
        msg = "🚨 *BIST QUANT RADAR: TOP 5*\n\n"
        for _, r in top.iterrows():
            msg += f"#{r['ticker']} | *Skor: {r['quant_score']:.1f}*\n"
            msg += f"• RVOL: {r['rvol_ratio']:.2f}x | HHI Yzd: %{r['pct_hhi']:.0f}\n"
            msg += f"• Fiyat: %{r['change_%']:.2f}\n\n"
        
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        except:
            print("Telegram hatasi.")

if __name__ == "__main__":
    run_pipeline()
