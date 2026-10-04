import numpy as np
import pandas as pd
FEATURES=['temperature','humidity','heat_index','temperature_lag1','humidity_lag1','heat_index_lag24','temperature_rolling24','humidity_rolling24','hour_sin','hour_cos','season_sin','season_cos']

def engineer(df):
    df=df.sort_values(['city_id','timestamp']).copy()
    g=df.groupby('city_id')
    # Every feature is available at the forecast origin, including current measurements.
    df['temperature_lag1']=g.temperature.shift(1)
    df['humidity_lag1']=g.humidity.shift(1)
    df['heat_index_lag24']=g.heat_index.shift(24)
    df['temperature_rolling24']=g.temperature.transform(lambda s:s.rolling(24,min_periods=24).mean())
    df['humidity_rolling24']=g.humidity.transform(lambda s:s.rolling(24,min_periods=24).mean())
    for name,values,period in [('hour',df.timestamp.dt.hour,24),('season',df.timestamp.dt.dayofyear,365.25)]:
        df[name+'_sin']=np.sin(2*np.pi*values/period)
        df[name+'_cos']=np.cos(2*np.pi*values/period)
    return df

def supervised(df,horizon):
    result=engineer(df)
    result['target']=result.groupby('city_id').heat_index.shift(-horizon)
    result['target_time']=result.groupby('city_id').timestamp.shift(-horizon)
    # Gaps cannot masquerade as hourly lags or targets.
    lag_time=result.groupby('city_id').timestamp.shift(24)
    valid=(result.target_time-result.timestamp==pd.Timedelta(hours=horizon)) & (result.timestamp-lag_time==pd.Timedelta(hours=24))
    return result[valid].dropna(subset=FEATURES+['target'])

