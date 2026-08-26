import numpy as np
import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore') # Pandas uyarılarını sustur

GECMIS_DOSYA = "gecmis_veri.csv"
RVOL_PENCERE = 20
MOM_PENCERE = 5 

def gecmis_veriyi_yukle():
    if os.path.exists(GECMIS_DOSYA):
        try:
            df = pd.read_csv(GECMIS_DOSYA)
            df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def calc_zscore(series):
    """Kurumsal düzey Z-Skor hesaplaması (Ayarlanmış)"""
    if len(series) < 2 or series.std() == 0:
        return 0.0
    return (series.iloc[-1] - series.mean()) / (series.std() + 1e-9)

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    scored_data = []

    for ticker in df['ticker']:
        # Güncel veriler
        current_data = df[df['ticker'] == ticker].iloc[0]
        
        # Geçmiş veri filtresi
        hist_df = df_gecmis[df_gecmis['ticker'] == ticker] if not df_gecmis.empty else pd.DataFrame()
        
        # Yeterli veri yoksa puanlamayı atla
        if hist_df.empty or len(hist_df) < MOM_PENCERE:
            scored_data.append({**current_data.to_dict(), 'quant_score': 0.0})
            continue

        # --- 1. CLOSING LOCATION VALUE (CLV) MICROSTRUCTURE ---
        # Hissenin gün içi dağıtım (distribution) veya toplama (accumulation) yediğini ölçer.
        _high = current_data['high']
        _low = current_data['low']
        _close = current_data['close']
        
        if _high - _low == 0: # Gün boyu işlem yoksa (Tavan/Taban)
            clv = 0.0
        else:
            clv = ((_close - _low) - (_high - _close)) / (_high - _low)
            
        # CLV Çarpanı (Smart Money Penalty)
        clv_multiplier = 1.0
        # Tepeden ağır satış yediyse ve gün içi yükselişliyse (Mal Kitleme Formasyonu)
        if clv < -0.4 and current_data['change_%'] > 2:
            clv_multiplier = 0.3 
        # Günü zirvede kapattıysa (Agresif Toplama)
        elif clv > 0.7:
            clv_multiplier = 1.2 

        # --- 2. RÖLATİF HACİM (RVOL) Z-SKORU ---
        hist_vol = hist_df['volume'].tail(RVOL_PENCERE)
        rvol_z = calc_zscore(hist_vol._append(pd.Series([current_data['volume']])))
        
        # Hacim Cezası: Z-Score > 3 ise bu 'Exhaustion' (Tükeniş/Klimaks) evresidir. Puan kırpılır.
        if rvol_z > 3.0: rvol_z = 1.5  
        elif rvol_z < 0: rvol_z = 0    

        # --- 3. YABANCI AKIŞI (FLOW DENSITY) ---
        hist_f = hist_df['foreign_ratio'].tail(MOM_PENCERE)
        f_delta = current_data['foreign_ratio'] - hist_f.iloc[0]
        
        hist_v = hist_df['value_traded'].tail(MOM_PENCERE)
        flow_dense = f_delta / (hist_v.mean() + 1e-9) if len(hist_v) > 0 else 0.0
        
        # --- 4. HHI MOMENTUM (KONSANTRASYON) ---
        hist_hhi = hist_df['hhi_score'].tail(MOM_PENCERE)
        hhi_mom = current_data['hhi_score'] - hist_hhi.iloc[0]

        # --- 5. VOLATİLİTEYE UYARLANMIŞ İVME (Sharpe Modeli) ---
        hist_returns = hist_df['change_%'].tail(RVOL_PENCERE)
        volatility = hist_returns.std() if len(hist_returns) > 5 else 1.0
        
        # Getiriyi Volatiliteye böl ve CLV (Gün sonu mikro-yapı) çarpanı ile çarp
        vol_adj_return = (current_data['change_%'] / (volatility + 1e-9)) * clv_multiplier
        
        # FOMO / Tavan Cezası: %8.5 üzeri fiyat artışlarını trenin son vagonu olarak değerlendir.
        if current_data['change_%'] > 8.5:
            vol_adj_return *= 0.5 

        # Ara puanları listeye ekle
        scored_data.append({
            **current_data.to_dict(),
            'rvol_z': rvol_z,
            'flow_dense': flow_dense,
            'hhi_mom': hhi_mom,
            'vol_adj_return': vol_adj_return
        })

    # Sonuçları DataFrame'e çevir
    res_df = pd.DataFrame(scored_data)
    if res_df.empty or ('quant_score' in res_df.columns and (res_df['quant_score'] == 0).all()):
        return res_df

    # --- NİHAİ NORMALİZASYON (MIN-MAX SCALING) ---
    # Rank (Yüzdelik) yerine verinin büyüklüğünü koruyan Z-Score/Min-Max matrisi
    for col in ['rvol_z', 'flow_dense', 'hhi_mom', 'vol_adj_return']:
        if col not in res_df.columns: continue
        min_val = res_df[col].min()
        max_val = res_df[col].max()
        if max_val - min_val == 0:
            res_df[f'{col}_norm'] = 0.0
        else:
            res_df[f'{col}_norm'] = (res_df[col] - min_val) / (max_val - min_val) * 100

    # --- ALGORİTMİK AĞIRLIKLANDIRMA (WEIGHTS) ---
    # %30 Gerçek Fiyat İvmesi + %25 Stabil Hacim + %25 Kurumsal Akış + %20 HHI
    res_df['quant_score'] = (
        res_df.get('vol_adj_return_norm', 0) * 0.30 +
        res_df.get('rvol_z_norm', 0) * 0.25 +
        res_df.get('flow_dense_norm', 0) * 0.25 +
        res_df.get('hhi_mom_norm', 0) * 0.20
    )

    # --- DÜNE GÖRE SKOR DEĞİŞİMİ (MOMENTUM) ---
    res_df['prev_quant_score'] = np.nan
    res_df['score_diff'] = 0.0
    
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        res_df['prev_quant_score'] = res_df['ticker'].map(eski_map).fillna(res_df['quant_score'])
        res_df['score_diff'] = res_df['quant_score'] - res_df['prev_quant_score']

    # Debug ve ara hesaplama kolonlarını temizleme
    drop_cols = ['rvol_z', 'flow_dense', 'hhi_mom', 'vol_adj_return', 
                 'rvol_z_norm', 'flow_dense_norm', 'hhi_mom_norm', 'vol_adj_return_norm']
    res_df = res_df.drop(columns=[col for col in drop_cols if col in res_df.columns])

    # En yüksek Quant Skoruna sahip olanları en üste al
    return res_df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
