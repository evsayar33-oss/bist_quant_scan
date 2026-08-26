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
            if 'tarih' in df.columns:
                df['tarih'] = pd.to_datetime(df['tarih'])
            return df
        except: return pd.DataFrame()
    return pd.DataFrame()

def calc_zscore(series):
    """Kurumsal düzey Z-Skor hesaplaması"""
    if len(series) < 2 or series.std() == 0:
        return 0.0
    return (series.iloc[-1] - series.mean()) / (series.std() + 1e-9)

def calculate_quant_scores(df, df_gecmis):
    if df.empty: return df

    scored_data = []

    for ticker in df['ticker']:
        current_data = df[df['ticker'] == ticker].iloc[0]
        
        # Hissenin geçmiş verisini bul (Varsa)
        hist_df = df_gecmis[df_gecmis['ticker'] == ticker] if not df_gecmis.empty else pd.DataFrame()

        # --- 1. CLOSING LOCATION VALUE (CLV) MICROSTRUCTURE ---
        _high = current_data['high']
        _low = current_data['low']
        _close = current_data['close']
        
        if _high - _low == 0: 
            clv = 0.0
        else:
            clv = ((_close - _low) - (_high - _close)) / (_high - _low)
            
        clv_multiplier = 1.0
        if clv < -0.4 and current_data['change_%'] > 2:
            clv_multiplier = 0.3 
        elif clv > 0.7:
            clv_multiplier = 1.2 

        # --- 2. GÜVENLİ GEÇMİŞ VERİ ÇEKİMİ (İlk Gün Koruması) ---
        # Eğer geçmiş veri yoksa hata vermez, anlık verilere göre hesaplar
        if not hist_df.empty:
            hist_vol = hist_df['volume'].tail(RVOL_PENCERE)
            hist_f = hist_df['foreign_ratio'].tail(MOM_PENCERE)
            hist_hhi = hist_df['hhi_score'].tail(MOM_PENCERE)
            hist_v = hist_df['value_traded'].tail(MOM_PENCERE)
            hist_returns = hist_df['change_%'].tail(RVOL_PENCERE)
            
            f_delta = current_data['foreign_ratio'] - hist_f.iloc[0]
            flow_dense = f_delta / (hist_v.mean() + 1e-9) if len(hist_v) > 0 else 0.0
            hhi_mom = current_data['hhi_score'] - hist_hhi.iloc[0]
            volatility = hist_returns.std() if len(hist_returns) > 2 else 1.0
        else:
            # Geçmiş veri yoksa (Yeni hisse veya sistemin ilk günü)
            hist_vol = pd.Series(dtype=float)
            flow_dense = 0.0
            hhi_mom = 0.0
            volatility = 1.0 # Volatilite bilinmediği için nötr

        # --- 3. RÖLATİF HACİM (RVOL) Z-SKORU ---
        combo_vol = pd.concat([hist_vol, pd.Series([current_data['volume']])], ignore_index=True)
        rvol_z = calc_zscore(combo_vol)
        
        if rvol_z > 3.0: rvol_z = 1.5  
        elif rvol_z < 0: rvol_z = 0    

        # --- 4. VOLATİLİTEYE UYARLANMIŞ İVME ---
        vol_adj_return = (current_data['change_%'] / (volatility + 1e-9)) * clv_multiplier
        
        if current_data['change_%'] > 8.5:
            vol_adj_return *= 0.5 

        scored_data.append({
            **current_data.to_dict(),
            'rvol_z': rvol_z,
            'flow_dense': flow_dense,
            'hhi_mom': hhi_mom,
            'vol_adj_return': vol_adj_return
        })

    res_df = pd.DataFrame(scored_data)
    if res_df.empty: return res_df

    # --- NİHAİ NORMALİZASYON ---
    for col in ['rvol_z', 'flow_dense', 'hhi_mom', 'vol_adj_return']:
        if col not in res_df.columns: continue
        min_val = res_df[col].min()
        max_val = res_df[col].max()
        if max_val - min_val == 0:
            res_df[f'{col}_norm'] = 0.0
        else:
            res_df[f'{col}_norm'] = (res_df[col] - min_val) / (max_val - min_val) * 100

    # --- ALGORİTMİK AĞIRLIKLANDIRMA ---
    res_df['quant_score'] = (
        res_df.get('vol_adj_return_norm', 0) * 0.30 +
        res_df.get('rvol_z_norm', 0) * 0.25 +
        res_df.get('flow_dense_norm', 0) * 0.25 +
        res_df.get('hhi_mom_norm', 0) * 0.20
    )

    # --- DÜNE GÖRE SKOR DEĞİŞİMİ ---
    res_df['prev_quant_score'] = np.nan
    res_df['score_diff'] = 0.0
    
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        res_df['prev_quant_score'] = res_df['ticker'].map(eski_map).fillna(res_df['quant_score'])
        res_df['score_diff'] = res_df['quant_score'] - res_df['prev_quant_score']

    drop_cols = ['rvol_z', 'flow_dense', 'hhi_mom', 'vol_adj_return', 
                 'rvol_z_norm', 'flow_dense_norm', 'hhi_mom_norm', 'vol_adj_return_norm']
    res_df = res_df.drop(columns=[col for col in drop_cols if col in res_df.columns])

    return res_df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
