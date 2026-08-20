import os
import requests
import pandas as pd
from datetime import datetime
import pytz
from data_fetcher import get_bist_tickers, get_takas_data
from quant_engine import calculate_hhi, calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id: return

    msg = "🇹🇷 *BIST QUANT LİDERLER (TOP 10)*\n"
    for _, r in df.head(10).iterrows():
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ({r['score_diff']:+.1f})\n"

    msg += "\n📉 *ÇIKIŞ RADARI (EN ÇOK DÜŞENLER)*\n"
    losers = df.sort_values(by='score_diff', ascending=True).head(10)
    for _, r in losers.iterrows():
        if r['score_diff'] < 0:
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

def run_pipeline():
    tr_tz = pytz.timezone('Europe/Istanbul')
    bugun = datetime.now(tr_tz).strftime('%Y-%m-%d')
    
    df = get_bist_tickers()
    if df.empty: return

    hhi_list = [calculate_hhi(get_takas_data(t)) for t in df['ticker']]
    df['hhi_score'] = hhi_list

    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)

    df.to_csv("sonuclar.csv", index=False)
    
    # Gecmise quant_score sütununu da ekleyerek kaydet
    df_kayit = df[['ticker', 'close', 'volume', 'change_%', 'hhi_score', 'quant_score']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df)

if __name__ == "__main__":
    run_pipeline()
