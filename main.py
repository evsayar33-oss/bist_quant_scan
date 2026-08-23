import os, requests, pandas as pd, pytz, time
from datetime import datetime
from data_fetcher import get_bist_tickers, get_takas_and_foreign_data
from quant_engine import calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def run_pipeline():
    tr_tz = pytz.timezone('Europe/Istanbul')
    bugun_str = datetime.now(tr_tz).strftime('%Y-%m-%d')
    
    df = get_bist_tickers()
    if df.empty: return

    print("Veri toplanıyor...")
    hhi_list, f_list = [], []
    for ticker in df['ticker']:
        h, f = get_takas_and_foreign_data(ticker)
        hhi_list.append(h); f_list.append(f)
        time.sleep(0.05)
    
    df['hhi_score'], df['foreign_ratio'] = hhi_list, f_list
    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)
    df.to_csv("sonuclar.csv", index=False)

    df_kayit = df[['ticker', 'close', 'volume', 'value_traded', 'change_%', 'hhi_score', 'foreign_ratio', 'quant_score']].copy()
    df_kayit['tarih'] = bugun_str
    if not df_gecmis.empty:
        if bugun_str not in df_gecmis['tarih'].dt.strftime('%Y-%m-%d').values:
            df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=False, index=False)
    else: df_kayit.to_csv(GECMIS_DOSYA, index=False)

    send_telegram_alert(df)

def send_telegram_alert(df):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if not token or not chat_id: return
    
    top = df.head(10)
    losers = df.sort_values(by='score_diff', ascending=True).head(10)

    msg = "🛡️ *BIST INSTITUTIONAL SENTINEL (TOP 10)*\n"
    for _, r in top.iterrows():
        msg += f"• #{r['ticker']} | *{r['quant_score']:.1f}* ({r['score_diff']:+.1f})\n"

    msg += "\n📉 *GÜÇ KAYBEDENLER (ÇIKIŞ RADARI)*\n"
    for _, r in losers.iterrows():
        if r['score_diff'] < -0.5:
            msg += f"• #{r['ticker']} | *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    run_pipeline()
