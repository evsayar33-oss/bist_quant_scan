import numpy as np
import pandas as pd
import os
 
GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20          # kendi ortalama hacmi icin gun sayisi
MIN_GECMIS_GUN = 5         # bu esigin altinda hisse "yeni/az gecmis" sayilir
 
 
def gecmis_veriyi_yukle():    """Var olan tarihsel kaydi yukler. Dosya yoksa bos DataFrame doner (ilk calistirma)."""
    if os.path.exists(GECMIS_DOSYA):
        return pd.read_csv(GECMIS_DOSYA, parse_dates=['tarih'])
    return pd.DataFrame(columns=['tarih', 'ticker', 'close', 'volume', 'change_%', 'hhi_score'])
 
 
def hisse_bazli_rvol_hesapla(df_bugun, df_gecmis, pencere=RVOL_PENCERE):
    """
    ESKI HATA: RVOL, o gunku tum BIST evrenine gore (cross-sectional) hesaplaniyordu.
    Bu, hep yuksek hacimli buyuk sirketleri one cikarir; kucuk/orta olcekli bir
    hissenin KENDI normaline gore anormal hacim artisini hic yakalamazdi.
 
    DUZELTME: Her hisse icin kendi son N gununun ortalama hacmine gore oran hesaplanir.
    RVOL = bugunku_hacim / son_N_gunun_ortalama_hacmi
    """
    rvol_oranlari = []
    for _, row in df_bugun.iterrows():
        ticker = row['ticker']
        gecmis_hacim = df_gecmis[df_gecmis['ticker'] == ticker]['volume'].tail(pencere)
        if len(gecmis_hacim) >= MIN_GECMIS_GUN:
            ort_hacim = gecmis_hacim.mean()
            rvol = row['volume'] / ort_hacim if ort_hacim > 0 else 1.0
        else:
            rvol = np.nan  # yetersiz gecmis - asagida evren medyaniyla doldurulur
        rvol_oranlari.append(rvol)
    df_bugun['rvol_ratio'] = rvol_oranlari
    return df_bugun
 
 
def calculate_hhi(takas_shares):
    """Herfindahl-Hirschman Indeksi (HHI) - takas/saklama yogunlasmasi. Degismedi."""
    if not takas_shares:
        return 0.0
    shares = np.array(takas_shares)
    if shares.sum() > 0:
        shares = (shares / shares.sum()) * 100
    return float(np.sum(shares ** 2))
 
 
def yuzdelik_dilim(seri):
    """
    Z-skor yerine yuzdelik dilim (percentile rank, 0-100).
    Volatil / aykiri-deger-egilimli bir evrende Z-skordan daha dayanikli;
    bilesik skoru da dogrudan yorumlanabilir (0-100) hale getirir.
    """
    return seri.rank(pct=True) * 100
 
 
def calculate_quant_scores(df, df_gecmis):
    """
    Bilesik Nicel Skor (0-100):
    QuantScore = 0.40 * Yzd(RVOL_kendi_gecmisine_gore)
               + 0.30 * Yzd(Fiyat_Degisim)
               + 0.30 * Yzd(Takas_HHI)
 
    ESKI HATA: HHI hesaplaniyordu ama formulde hic kullanilmiyordu.
    DUZELTME: HHI artik ilan edilen %30 agirlikla skora fiilen dahil.
    """
    if df.empty: return df
 
    # 1) Hisse-bazli (kendi gecmisine gore) RVOL orani
    df = hisse_bazli_rvol_hesapla(df, df_gecmis)
    yeterli_gecmis = df['rvol_ratio'].notna()
 
    # Yeterli gecmisi olmayan (yeni/az islem gormus) hisseler icin evren medyani ile doldur.
    # Medyan = notr deger: ne odullendirir ne cezalandirir, sadece skoru bozmaz.
    medyan_rvol = df.loc[yeterli_gecmis, 'rvol_ratio'].median() if yeterli_gecmis.any() else 1.0
    df['rvol_ratio'] = df['rvol_ratio'].fillna(medyan_rvol)
    df['gecmis_yetersiz'] = ~yeterli_gecmis  # seffaflik icin: bu hisseye guvenilir RVOL yok
 
    # 2) Yuzdelik dilim bazli alt skorlar
    df['pct_rvol'] = yuzdelik_dilim(df['rvol_ratio'])
    df['pct_change'] = yuzdelik_dilim(df['change_%'])
    df['pct_hhi'] = yuzdelik_dilim(df['hhi_score'])
 
    # 3) Bilesik skor - ilan edilen agirliklar artik fiilen uygulaniyor
    df['quant_score'] = (
        0.40 * df['pct_rvol'] +
        0.30 * df['pct_change'] +
        0.30 * df['pct_hhi']
    )
 
    df = df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
    return df
 
