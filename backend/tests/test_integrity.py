import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.data import cities,observations
from app.core.config import DATA
from app.geospatial.join import join_locations
import pandas as pd

def test_dataset_ranges_uniqueness_and_geographic_join():
    df=observations()
    assert df.temperature.between(10,50).all()
    assert df.humidity.between(0,100).all()
    assert not df.duplicated(['city_id','timestamp']).any()
    assert df.timestamp.notna().all()
    joined=join_locations(DATA/'boundaries.geojson',pd.DataFrame(cities()))
    assert len(joined)==17 and joined.geometry.is_valid.all()

def test_simulator_vegetation_does_not_invent_cooling():
    client=TestClient(app);city=cities()[0]['city_id']
    response=client.post('/api/simulation',json=dict(city_id=city,vegetation_change=20))
    assert response.status_code==422
    unchanged=client.post('/api/simulation',json=dict(city_id=city)).json()['data']
    assert unchanged['scenario']['vegetation'] is None
    assert unchanged['difference']['heat_index']==0
    assert client.post('/api/simulation',json=dict(city_id=city,vegetation_change=100)).status_code==422

def test_models_have_real_metrics_and_inference():
    client=TestClient(app)
    registry=client.get('/api/model/metrics').json()['data']
    assert len(registry['metrics'])==4
    assert all(m['mae']>=0 for m in registry['metrics'])
    r=client.get('/api/forecast',params={'city_id':cities()[0]['city_id'],'horizon':6})
    assert r.status_code==200
    p=r.json()['data'];assert p['lower']<p['heat_index']<p['upper']
    assert client.get('/api/forecast',params={'city_id':cities()[0]['city_id'],'horizon':7}).status_code==422

def test_import_preview_rejects_invalid_without_saving(monkeypatch):
    monkeypatch.setenv('ADMIN_TOKEN','test-token')
    client=TestClient(app)
    csv=f'timestamp,city_id,temperature,humidity\n2026-01-01,{cities()[0]["city_id"]},99,120\n'
    r=client.post('/api/import/preview',files={'file':('invalid.csv',csv)},headers={'X-Admin-Token':'test-token'})
    assert r.status_code==200 and not r.json()['data']['valid'] and not r.json()['data']['saved']

def test_real_data_provenance():
    df=observations()
    assert set(df.provenance)=={'reanalysis'}
    assert len(df)==148920
    assert sum(c['population'] for c in cities())==13484462
    assert all(c['vegetation'] is None and c['built_up'] is None for c in cities())
    assert len({(c['weather_grid_latitude'],c['weather_grid_longitude']) for c in cities()})==6

