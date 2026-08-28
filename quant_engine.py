import numpy as np
import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore')

GECMIS_DOSYA = "gecmis_veri.csv"

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        try:
            df = pd.read_csv(GECMIS_DOSYA)
            if 'tarih' in df.columns:
                df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except: 
            return pd.DataFrame()
    return pd.DataFrame()

def calculate_quant_scores(df, df_gecmis):
    if df.empty: 
        return df

    scored_data = []

    for idx, row in df.iterrows():
        item = row.to_dict()
        
        close = float(item.get('close', 0.0))
        sma50 = float(item.get('sma50', 0.0))
        sma200 = float(item.get('sma200', 0.0))
        perf_1m = float(item.get('perf_1m', 0.0))
        rvol = float(item.get('rvol', 1.0))
        cmf = float(item.get('cmf', 0.0))
        rsi = float(item.get('rsi', 50.0))
        
        bb_upper = float(item.get('bb_upper', 0.0))
        bb_lower = float(item.get('bb_lower', 0.0))
        bb_basis = float(item.get('bb_basis', 0.0))
        kelt_upper = float(item.get('kelt_upper', 0.0))
        kelt_lower = float(item.get('kelt_lower', 0.0))
        donch_upper = float(item.get('donch_upper', 0.0))

        # =========================================================================
        # 1. ANTİ-FOMO / AŞIRI ŞİŞME DİSKALİFİYE FİLTRESİ (258 TL PASEU ENGELİ)
        # =========================================================================
        is_overextended = False
        
        # Kural A: Fiyat SMA50'den %22'den fazla uzaklaşmışsa (Tepede)
        if sma50 > 0 and (close / sma50) > 1.22:
            is_overextended = True
            
        # Kural B: Fiyat SMA200'den %45'ten fazla uzaklaşmışsa
        if sma200 > 0 and (close / sma200) > 1.45:
            is_overextended = True
            
        # Kural C: Hisse son 1 ayda zaten %45'ten fazla prim yapmışsa (Tren kaçmış)
        if perf_1m > 45.0:
            is_overextended = True

        # =========================================================================
        # 2. VOLATİLİTE SIKIŞMASI (JOHN CARTER SQUEEZE & BBW)
        # =========================================================================
        # Bollinger Bant Genişliği (Ne kadar darsa o kadar büyük patlama potansiyeli)
        bbw = (bb_upper - bb_lower) / (bb_basis + 1e-9) if bb_basis > 0 else 0.5
        
        # Squeeze Durumu: Bollinger Keltner'in içine girdi mi? (Yay sıkışması)
        in_squeeze = (bb_upper <= kelt_upper) and (bb_lower >= kelt_lower)
        
        # Sıkışma Puanı (0 - 100)
        squeeze_score = 0.0
        if in_squeeze:
            squeeze_score += 50.0
        if bbw < 0.12: # Aşırı dar bant (Bomba hazır)
            squeeze_score += 50.0
        elif bbw < 0.20:
            squeeze_score += 30.0

        # =========================================================================
        # 3. TABANDAN İLK KOPUŞ & DONCHIAN KIRILIMI (KIRMIZI OK NOKTASI)
        # =========================================================================
        breakout_score = 0.0
        
        # Kural: Fiyat SMA50'ye çok yakın olacak (Taban bölgesi)
        dist_sma50 = (close - sma50) / (sma50 + 1e-9) if sma50 > 0 else 0.0
        if -0.03 <= dist_sma50 <= 0.08: # SMA50'nin hemen üstünde veya tam kırma anında
            breakout_score += 40.0
        elif 0.08 < dist_sma50 <= 0.15:
            breakout_score += 20.0
            
        # Kural: 20 Günlük Donchian Zirvesi Kırılımı (Kopuş teyidi)
        if donch_upper > 0 and close >= (donch_upper * 0.985):
            breakout_score += 35.0
            
        # Kural: Stage 2 Yapısı (SMA50 > SMA200 veya SMA200'ün üzerine yeni atış)
        if sma50 > sma200 and sma200 > 0:
            breakout_score += 25.0

        # =========================================================================
        # 4. SESSİZ KURUMSAL TOPLAMA (ACCUMULATION & VOLUME IGNITION)
        # =========================================================================
        volume_score = 0.0
        if rvol > 1.8: # Kırılım anında hacim patlaması
            volume_score += 40.0
        elif rvol > 1.2:
            volume_score += 20.0
            
        if cmf > 0.08: # Pozitif para girişi
            volume_score += 35.0
        elif cmf > 0.0:
            volume_score += 15.0
            
        if 50.0 <= rsi <= 68.0: # Aşırı alımda değil, sağlıklı momentum bölgesinde
            volume_score += 25.0

        # =========================================================================
        # 5. BİLEŞİK TREND BAŞLANGIÇ SKORU (QUANT SCORE)
        # =========================================================================
        if is_overextended:
            # Aşırı şişmiş hisseler doğrudan 0 puan alır ve listelenmez
            quant_score = 0.0
            status_tag = "🚫 AŞIRI ŞİŞMİŞ (TEPE)"
        else:
            # %35 Sıkışma Kalitesi + %40 Tabandan Kopuş + %25 Hacim/Akış
            quant_score = (squeeze_score * 0.35) + (breakout_score * 0.40) + (volume_score * 0.25)
            quant_score = round(min(quant_score, 100.0), 2)
            
            if quant_score >= 70.0:
                status_tag = "🎯 TREND BAŞLANGICI (GÜÇLÜ)"
            elif quant_score >= 50.0:
                status_tag = "⚡ SIKIŞMADAN KOPUŞ (ADAY)"
            else:
                status_tag = "NÖTR"

        item['quant_score'] = quant_score
        item['bbw'] = round(bbw, 3)
        item['status_tag'] = status_tag
        scored_data.append(item)

    res_df = pd.DataFrame(scored_data)
    if res_df.empty: 
        return res_df

    # Düne göre puan farkı
    res_df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        res_df['score_diff'] = np.round(res_df['quant_score'] - res_df['ticker'].map(eski_map).fillna(res_df['quant_score']), 2)

    return res_df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
