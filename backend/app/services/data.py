import json, os
from functools import lru_cache
import pandas as pd
from app.core.config import DATA, CONFIG
from app.analytics.heat import exposure_index, risk

@lru_cache
def cities():
    return json.loads((DATA/'cities.json').read_text(encoding='utf-8-sig'))

@lru_cache
def observations():
    if os.getenv('DATABASE_URL'):
        from sqlalchemy import create_engine, text
        with create_engine(os.environ['DATABASE_URL']).connect() as connection:
            df = pd.read_sql(text('SELECT o.* FROM observations o WHERE dataset_id=:version'), connection, params={'version':CONFIG['version']})
    else:
        df = pd.read_csv(DATA/'clean.csv',dtype={'city_id':str})
    df['timestamp']=pd.to_datetime(df.timestamp,utc=True).dt.tz_convert('Asia/Manila')
    return df

def snapshot(date='2026-09-30', hour=14, city_id=None):
    df = observations()
    target=pd.Timestamp(f'{date} {hour:02}:00',tz='Asia/Manila')
    df=df[df.timestamp==target].merge(pd.DataFrame(cities()),on='city_id')
    if city_id: df=df[df.city_id==city_id]
    df['exposure_index']=exposure_index(df.heat_index,df.population_density,df.vegetation,df.built_up).round(2)
    df['risk']=df.exposure_index.map(risk)
    df['exposed_population']=df.population.where(df.exposure_index>=CONFIG['elevated_min'],0)
    return df

def records(df):
    return json.loads(df.to_json(orient='records',date_format='iso'))

