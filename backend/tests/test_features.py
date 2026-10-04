import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from app.ml.features import engineer,supervised

def test_no_cross_city_lag_or_future_feature_leakage():
    base=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=100,freq='h',tz='Asia/Manila'),'city_id':'a','temperature':range(100),'humidity':50,'heat_index':range(100)})
    other=base.assign(city_id='b',temperature=1000)
    features=engineer(pd.concat([base,other]))
    assert features[features.city_id=='b'].temperature_lag1.iloc[0]!=features[features.city_id=='b'].temperature_lag1.iloc[0]
    row=features[(features.city_id=='a')].iloc[24]
    assert row.temperature_lag1==23 and row.heat_index_lag24==0
    assert row.temperature_rolling24==12.5
    supervised_data=supervised(base,6)
    assert (supervised_data.target-supervised_data.heat_index==6).all()

def test_gaps_rejected():
    base=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=100,freq='h',tz='Asia/Manila'),'city_id':'a','temperature':30,'humidity':50,'heat_index':35})
    gapped=base.drop(index=30)
    data=supervised(gapped,6)
    assert not ((data.timestamp>='2026-01-02 06:00+08:00')&(data.timestamp<'2026-01-03 07:00+08:00')).any()

