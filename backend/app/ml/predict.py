from functools import lru_cache
import joblib
import pandas as pd
from app.core.config import ROOT,CONFIG
from app.services.data import observations,cities
from app.ml.features import engineer,FEATURES
from app.analytics.heat import exposure_index,risk

@lru_cache
def artifact():
    path=ROOT/'backend/artifacts'/(CONFIG['version']+'.joblib')
    if not path.exists(): raise FileNotFoundError('Train the local model before requesting live API inference')
    return joblib.load(path) # Only load this application-generated artifact; never user uploads.

def predict(city_id,horizon):
    saved=artifact();entry=saved['models'][horizon]
    recent=engineer(observations().query('city_id == @city_id')).tail(1)
    model=entry['model'];value=float(recent.heat_index.iloc[0] if model is None else model.predict(recent[FEATURES])[0])
    c=next(c for c in cities() if c['city_id']==city_id)
    return dict(city_id=city_id,horizon=horizon,timestamp=(recent.timestamp.iloc[0]+pd.Timedelta(hours=horizon)).isoformat(),heat_index=value,lower=value-entry['interval_half_width'],upper=value+entry['interval_half_width'],risk=risk(float(exposure_index(value,c['population_density'],c['vegetation'],c['built_up']))))

