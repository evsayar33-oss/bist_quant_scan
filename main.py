import pandas as pd
import os
import requests
from datetime import datetime

from data_fetcher import fetch_all_data
from quant_engine import calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

def send_telegram_message(message):
    """GitHub Secrets üzerinden token alıp Telegram'a formatlı mesaj atar."""
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("Uyarı: TELEGRAM_TOKEN veya CHAT_ID bulunamadı! Mesaj gönderilmeyecek.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram mesajı başarıyla gönderildi!")
        else:
            print(f"Telegram Hatası: {response.text}")
    except Exception as e:
        print(f"Telegram gönderiminde kritik hata: {e}")

def format_quant_report(df_scored):
    """DataFrame'den en iyi 10 ve en kötü 10 hisseyi seçip Telegram HTML mesajı oluşturur."""
    
    # 1. Liderler: Quant Skoru en yüksek 10 hisse
    top10 = df_scored.sort_values(by='quant_score', ascending=False).head(10)
    
    # 2. Çıkış Radarı: Skoru düne göre en çok düşen 10 hisse
    if 'score_diff' in df_scored.columns:
        worst10 = df_scored.sort_values(by='score_diff', ascending=True).head(10)
        # Eğer henüz düne ait veri yoksa (Farklar sıfırsa) listeyi boşalt
        if (worst10['score_diff'] == 0).all():
            worst10 = pd.DataFrame()
    else:
        worst10 = pd.DataFrame()

    # --- HTML MESAJ ŞABLONU ---
    msg = f"📊 <b>BIST Quant Alpha Günlük Rapor</b>\n"
    msg += f"🗓 <i>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n\n"
    
    msg += "🏆 <b>KURUMSAL ONAYLI LİDERLER (Top 10)</b>\n"
    msg += "<i>(Hacim, Mikro-Yapı ve Yabancı Akışı Onaylı)</i>\n"
    for idx, row in top10.iterrows():
        fark_gostergesi = f"(+{row['score_diff']:.1f})" if row.get('score_diff', 0) > 0 else f"({row.get('score_diff', 0):.1f})"
        msg += f"• <b>{row['ticker']}</b> : Puan: <b>{row['quant_score']:.1f}</b> <i>{fark_gostergesi}</i> | Fiyat: %{row.get('change_%', 0):.1f}\n"
        
    if not worst10.empty:
        msg += "\n🚨 <b>ÇIKIŞ RADARI (Skoru En Çok Düşenler)</b>\n"
        msg += "<i>(Trend Tükenişi veya Kurumsal Çıkış Gözlenenler)</i>\n"
        for idx, row in worst10.iterrows():
            msg += f"• <b>{row['ticker']}</b> : Puan: <b>{row['quant_score']:.1f}</b> | Düşüş: <b>{row['score_diff']:.1f}</b>\n"
            
    msg += "\n⚡️ <i>Sistem: Tier-1 Alpha Overlay Motoru</i>"
    
    return msg


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === BIST Quant Alpha Scanner Başlıyor ===")
    
    # 1. VERİ TOPLAMA
    df_current = fetch_all_data()
    if df_current.empty:
        print("Hata: Piyasa verisi çekilemedi. İşlem iptal edildi.")
        return

    # 2. GEÇMİŞ VERİYİ YÜKLE
    df_gecmis = gecmis_veriyi_yukle()
    
    # 3. HESAPLAMA MOTORU
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quant motoru çalışıyor (CLV ve Z-Skorlar hesaplanıyor)...")
    df_scored = calculate_quant_scores(df_current, df_gecmis)
    
    if df_scored.empty:
        print("Puanlanmış veri boş döndü.")
        return

    # 4. GEÇMİŞ VERİ TABANINI GÜNCELLEME (CSV)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Veritabanı güncelleniyor...")
    if not df_gecmis.empty:
        bugun = pd.Timestamp.now().normalize()
        df_gecmis = df_gecmis[df_gecmis['tarih'] != bugun]
        df_yeni_gecmis = pd.concat([df_gecmis, df_scored], ignore_index=True)
    else:
        df_yeni_gecmis = df_scored
        
    df_yeni_gecmis['tarih'] = pd.to_datetime(df_yeni_gecmis['tarih'])
    limit_tarih = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)
    df_yeni_gecmis = df_yeni_gecmis[df_yeni_gecmis['tarih'] >= limit_tarih]
    
    df_yeni_gecmis.to_csv(GECMIS_DOSYA, index=False)
    
    # 5. TELEGRAM RAPORU GÖNDERİMİ
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Telegram raporu hazırlanıyor...")
    telegram_msg = format_quant_report(df_scored)
    send_telegram_message(telegram_msg)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sistem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
