import os
import requests
import pandas as pd
from datetime import datetime
import pytz
from data_fetcher import get_bist_tickers, get_takas_data
from quant_engine import calculate_hhi, calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def run_pipeline():
    tr_tz = pytz.timezone('Europe/Istanbul')
    bugun_dt = datetime.now(tr_tz)
    bugun_str = bugun_dt.strftime('%Y-%m-%d')
    
    print(f"Tarama Başladı: {bugun_str}")
    
    df = get_bist_tickers()
    if df.empty: return

    print("Takas verileri çekiliyor...")
    hhi_list = []
    for ticker in df['ticker']:
        shares = get_takas_data(ticker)
        hhi_list.append(calculate_hhi(shares))
    df['hhi_score'] = hhi_list

    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)

    # Dashboard dosyası
    df.to_csv("sonuclar.csv", index=False)

    # Geçmişe kaydet (Hizalama sütunları)
    df_kayit = df[['ticker', 'close', 'volume', 'change_%', 'hhi_score', 'quant_score']].copy()
    df_kayit['tarih'] = bugun_str
    
    if not df_gecmis.empty:
        tarih_list = df_gecmis['tarih'].dt.strftime('%Y-%m-%d').unique()
        if bugun_str not in tarih_list:
            df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=False, index=False)
    else:
        df_kayit.to_csv(GECMIS_DOSYA, index=False)

    send_telegram_alert(df)

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id: return

    top_10 = df.head(10)
    # Skoru en çok düşen 10 hisse
    losers_10 = df.sort_values(by='score_diff', ascending=True).head(10)

    msg = "🏆 *BIST QUANT LİDERLER (TOP 10)*\n"
    for _, r in top_10.iterrows():
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ({r['score_diff']:+.1f})\n"

    msg += "\n📉 *SKORU EN ÇOK DÜŞENLER (TOP 10)*\n"
    for _, r in losers_10.iterrows():
        if r['score_diff'] < 0:
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    run_pipeline()
