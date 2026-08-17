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
    
    df = get_bist_tickers()
    if df.empty: return

    hhi_list = []
    for ticker in df['ticker']:
        shares = get_takas_data(ticker)
        hhi_list.append(calculate_hhi(shares))
    df['hhi_score'] = hhi_list

    df_gecmis = gecmis_veriyi_yukle()
    df = calculate_quant_scores(df, df_gecmis)

    df.to_csv("sonuclar.csv", index=False)

    # Geçmişe kaydet
    df_kayit = df[['ticker', 'close', 'volume', 'change_%', 'hhi_score', 'quant_score']].copy()
    df_kayit['tarih'] = bugun_str
    
    if not df_gecmis.empty:
        # Tarih kontrolünü string bazlı yapalım
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

    top_rank = df.head(10)
    # Sadece anlamlı farkı olanları al
    gainers = df[df['score_diff'] > 0.1].sort_values(by='score_diff', ascending=False).head(10)
    losers = df[df['score_diff'] < -0.1].sort_values(by='score_diff', ascending=True).head(10)

    msg = "🏆 *BIST QUANT LİDERLER*\n"
    for _, r in top_rank.iterrows():
        diff = f"({r['score_diff']:+.1f})" if not pd.isna(r['prev_quant_score']) else "(Yeni)"
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* {diff}\n"

    msg += "\n🚀 *ATAK YAPANLAR*\n"
    if gainers.empty:
        msg += "_Henüz yeterli kıyas verisi yok._\n"
    else:
        for _, r in gainers.iterrows():
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* 🔥 {r['score_diff']:+.1f}\n"

    msg += "\n📉 *GÜÇ KAYBEDENLER*\n"
    if losers.empty:
        msg += "_Henüz yeterli kıyas verisi yok._\n"
    else:
        for _, r in losers.iterrows():
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:+.1f}\n"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

if __name__ == "__main__":
    run_pipeline()
