import pandas as pd
import os
from datetime import datetime

# YENİ MİMARİ İMPORTLARI
from data_fetcher import fetch_all_data
from quant_engine import calculate_quant_scores, gecmis_veriyi_yukle, GECMIS_DOSYA

# Eğer telegram bildirim dosyan varsa (örneğin telegram_bot.py veya notifier.py gibi),
# kendi eski main.py'ndaki o importları buraya eklemeyi unutma.
# Örnek: from telegram_bot import send_signals

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === BIST Quant Alpha Scanner Başlıyor ===")
    
    # 1. VERİ TOPLAMA (Eski for döngüleri yerine yeni Asenkron motor tek satırda her şeyi halleder)
    df_current = fetch_all_data()
    
    if df_current.empty:
        print("Hata: Piyasa veya Takas verisi çekilemedi. İşlem iptal edildi.")
        return

    # 2. GEÇMİŞ VERİYİ YÜKLE
    df_gecmis = gecmis_veriyi_yukle()
    
    # 3. HESAPLAMA (CLV, Z-Score, Sharpe Modeli)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quant motoru çalışıyor (Mikroyapı ve Z-Skorlar hesaplanıyor)...")
    df_scored = calculate_quant_scores(df_current, df_gecmis)
    
    if df_scored.empty:
        print("Puanlanmış veri boş döndü.")
        return

    # 4. GEÇMİŞ VERİ TABANINI GÜNCELLEME (CSV)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Veritabanı güncelleniyor...")
    if not df_gecmis.empty:
        # Aynı gün tekrar çalıştırılırsa verileri çoğaltmamak için, bugünün verisini eskiden temizle
        bugun = pd.Timestamp.now().normalize()
        df_gecmis = df_gecmis[df_gecmis['tarih'] != bugun]
        
        df_yeni_gecmis = pd.concat([df_gecmis, df_scored], ignore_index=True)
    else:
        df_yeni_gecmis = df_scored
        
    # Sadece son 30 günün verisini tutarak CSV'nin şişmesini/yavaşlamasını engelliyoruz
    df_yeni_gecmis['tarih'] = pd.to_datetime(df_yeni_gecmis['tarih'])
    limit_tarih = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)
    df_yeni_gecmis = df_yeni_gecmis[df_yeni_gecmis['tarih'] >= limit_tarih]
    
    # CSV'ye yaz
    df_yeni_gecmis.to_csv(GECMIS_DOSYA, index=False)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Başarılı! Sonuçlar {GECMIS_DOSYA} dosyasına kaydedildi.")
    
    # 5. EĞER TELEGRAM BOTUN VARSA KODUNU BURAYA EKLE
    # İlk 10 hisseyi Telegrama göndermek için örnek kod mantığı:
    # top_10_hisse = df_scored.head(10)
    # send_signals(top_10_hisse)
    print("En yüksek puanlı ilk 5 hisse:")
    print(df_scored[['ticker', 'quant_score', 'change_%', 'volume']].head(5))

if __name__ == "__main__":
    main()
