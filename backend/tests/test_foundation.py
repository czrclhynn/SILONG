import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app.analytics.heat import heat_index, exposure_index
from app.pipeline.cleaning import clean_observations
from app.main import app

def test_heat_index_reference():
    # NOAA example: 90 F at 70% RH is approximately 105.9 F.
    assert float(heat_index(32.222222,70)) == pytest.approx(41.1,abs=.2)
    assert float(heat_index(20,50)) < 22
    with pytest.raises(ValueError): heat_index(30,101)

def test_validation():
    df=pd.DataFrame({'timestamp':['2026-01-01']*4,'city_id':['x','x','x','bad'],'temperature':[30,31,99,30],'humidity':[60]*4})
    out,stats=clean_observations(df,{'x'})
    assert len(out)==1 and stats['duplicates_removed']==1 and stats['invalid_observations']==2
    assert out.timestamp.iloc[0].hour==0

def test_index_monotonic_and_clipped():
    # Active real-data screening must not invent environmental effects.
    assert exposure_index(40,20000,50,70)==exposure_index(40,20000,10,70)
    assert exposure_index(45,20000,None,None)>exposure_index(35,20000,None,None)
    assert 0<=exposure_index(100,100000,0,100)<=100

def test_api_and_simulation():
    client=TestClient(app)
    cities=client.get('/api/locations').json()['data']
    assert len(cities)==17
    assert client.get('/api/overview?hour=99').status_code==422
    assert client.get('/api/overview?date=1900-01-01').status_code==404
    baseline=client.get('/api/overview').json()['data']
    assert baseline['exposed_population']<=sum(c['population'] for c in cities)
    result=client.post('/api/simulation',json={'city_id':cities[0]['city_id']}).json()['data']
    assert result['difference']['heat_index']==pytest.approx(0,abs=.01)
    assert abs(result['difference']['exposure_index'])<.01
    assert client.post('/api/simulation',json={'city_id':'bad'}).status_code==404
    assert client.post('/api/import/preview',files={'file':('a.csv',b'a,b')}).status_code==403

