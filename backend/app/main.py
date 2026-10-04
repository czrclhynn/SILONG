from datetime import date as Date
import json, os, secrets, io, hashlib, uuid
from typing import Literal
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Header, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CONFIG, DATA
from app.services.data import cities, observations, snapshot, records
from app.schemas.models import Envelope, SimulationInput
from app.analytics.heat import heat_index, exposure_index, risk
from app.pipeline.cleaning import clean_observations

app=FastAPI(title='SILONG Urban Heat Intelligence',version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Admin-Token'])

def result(data, provenance=CONFIG.get('provenance','synthetic')): return Envelope(data=data,provenance=provenance)
def get_snapshot(date, hour, city_id=None):
    if city_id and city_id not in {x['city_id'] for x in cities()}: raise HTTPException(404,'Unknown city identifier')
    df=snapshot(str(date),hour,city_id)
    if df.empty: raise HTTPException(404,'No data available for the selected period.')
    return df

@app.get('/health')
def health(): return {'status':'ok','dataset':CONFIG['version']}

@app.get('/api/demo')
@app.get('/api/dataset')
def demo_bundle():
    from app.core.config import ROOT
    return FileResponse(ROOT/'frontend/public/data/dataset.json',media_type='application/json')

@app.get('/api/locations',response_model=Envelope)
def locations(): return result(cities())

@app.get('/api/locations/{city_id}',response_model=Envelope)
def location(city_id:str,date:Date=Date(2025,12,31),hour:int=Query(14,ge=0,le=23)):
    return result(records(get_snapshot(date,hour,city_id))[0])

@app.get('/api/overview',response_model=Envelope)
def overview(date:Date=Date(2025,12,31),hour:int=Query(14,ge=0,le=23),city_id:str|None=None):
    df=get_snapshot(date,hour,city_id)
    baseline=snapshot(str(date-pd.Timedelta(days=1)),hour,city_id)
    return result(dict(heat_index=round(float(df.heat_index.mean()),2),temperature=round(float(df.temperature.mean()),2),
        humidity=round(float(df.humidity.mean()),2),exposed_population=int(df.exposed_population.sum()),
        highest_risk_area=df.loc[df.exposure_index.idxmax(),'name'],
        trend=None if baseline.empty else round(float(df.heat_index.mean()-baseline.heat_index.mean()),2),
        baseline='Previous day, same local hour',locations=records(df)))

@app.get('/api/exposure',response_model=Envelope)
def exposure(date:Date=Date(2025,12,31),hour:int=Query(14,ge=0,le=23)):
    df=get_snapshot(date,hour)
    counts=df.groupby('risk').population.sum()
    return result([dict(category=x['label'],population=int(counts.get(x['label'],0)),color=x['color']) for x in CONFIG['risk_thresholds']])

@app.get('/api/heat/trends',response_model=Envelope)
def trends(city_id:str|None=None,start:Date=Date(2025,12,1),end:Date=Date(2025,12,31),group:Literal['hour','day','week','month','year']='day'):
    if start>end: raise HTTPException(422,'Start must precede end')
    df=observations()
    if city_id:
        if city_id not in {x['city_id'] for x in cities()}: raise HTTPException(404,'Unknown city identifier')
        df=df[df.city_id==city_id]
    df=df[(df.timestamp.dt.date>=start)&(df.timestamp.dt.date<=end)]
    rule={'hour':'h','day':'D','week':'W','month':'MS','year':'YS'}[group]
    out=df.set_index('timestamp')[['heat_index','temperature','humidity']].resample(rule).mean().dropna().reset_index()
    return result(records(out))

@app.get('/api/data-quality',response_model=Envelope)
def quality(): return result(json.loads((DATA/'quality.json').read_text(encoding='utf-8-sig')))

@app.get('/api/methodology',response_model=Envelope)
def methodology(): return result(CONFIG,'methodology')

@app.get('/api/analytics',response_model=Envelope)
def analytics_endpoint():
    from app.analytics.explore import analytics
    return result(analytics())

@app.get('/api/hotspots',response_model=Envelope)
def hotspots():
    from app.analytics.explore import analytics
    return result(sorted(analytics()['city_stats'],key=lambda x:x['elevated_frequency'],reverse=True))

@app.get('/api/model/metrics',response_model=Envelope)
def model_metrics():
    path=DATA/'forecasts.json'
    if not path.exists(): raise HTTPException(503,'No trained model available. Run scripts/train_models.py.')
    return result(json.loads(path.read_text(encoding='utf-8-sig'))['registry'],'model-evaluation-on-reanalysis')

@app.get('/api/forecast',response_model=Envelope)
def forecast(city_id:str,horizon:int=6):
    if horizon not in (6,12,24): raise HTTPException(422,'Supported horizons are 6, 12, and 24 hours.')
    if city_id not in {c['city_id'] for c in cities()}: raise HTTPException(404,'Unknown city identifier')
    from app.ml.predict import predict
    try: return result(predict(city_id,horizon),'predicted-from-reanalysis')
    except FileNotFoundError: raise HTTPException(503,'Model artifact unavailable. Run model training.')

@app.post('/api/simulation',response_model=Envelope)
def simulation(body:SimulationInput):
    try: date=Date.fromisoformat(body.date)
    except ValueError: raise HTTPException(422,'Invalid date')
    base=records(get_snapshot(date,body.hour,body.city_id))[0]
    if base['vegetation'] is None and (body.vegetation_change or body.built_up!='baseline'):
        raise HTTPException(422,'Vegetation and built-up scenarios require verified baseline measurements, which are unavailable.')
    scenario=dict(base)
    scenario.update(temperature=base['temperature']+body.temperature_change,
        humidity=float(np.clip(base['humidity']+body.humidity_change,0,100)),
        vegetation=None if base['vegetation'] is None else min(100,base['vegetation']+body.vegetation_change),
        population_density=base['population_density']*(1+body.density_change/100),
        population=round(base['population']*(1+body.density_change/100)),
        built_up={'low':35,'medium':60,'high':85}.get(body.built_up,base['built_up']))
    scenario['heat_index']=round(float(heat_index(scenario['temperature'],scenario['humidity'])),2)
    scenario['exposure_index']=round(float(exposure_index(scenario['heat_index'],scenario['population_density'],scenario['vegetation'],scenario['built_up'])),2)
    scenario['risk']=risk(scenario['exposure_index'])
    scenario['exposed_population']=scenario['population'] if scenario['exposure_index']>=CONFIG['elevated_min'] else 0
    return result(dict(baseline=base,scenario=scenario,difference={key:scenario[key]-base[key] for key in ['heat_index','exposure_index','exposed_population']},method=CONFIG['simulation_method']),'simulated')

@app.post('/api/import/preview',response_model=Envelope)
async def preview(file:UploadFile=File(...),x_admin_token:str|None=Header(None)):
    token=os.getenv('ADMIN_TOKEN')
    if not token or not x_admin_token or not secrets.compare_digest(token,x_admin_token): raise HTTPException(403,'Admin import is disabled or the token is invalid.')
    content=await file.read(5_000_001)
    if len(content)>5_000_000: raise HTTPException(413,'Maximum file size is 5 MB')
    try:
        if file.filename and file.filename.lower().endswith('.csv'):
            df=pd.read_csv(io.BytesIO(content),dtype={'city_id':str})
            clean,stats=clean_observations(df,{x['city_id'] for x in cities()})
            stats.update(columns=list(df.columns),cities_detected=clean.city_id.unique().tolist(),date_range=[str(clean.timestamp.min()),str(clean.timestamp.max())],valid=stats['invalid_observations']==0 and len(clean)>0, saved=False,sha256=hashlib.sha256(content).hexdigest())
            return result(stats,'upload-preview')
        if file.filename and file.filename.lower().endswith('.geojson'):
            from shapely.geometry import shape
            document=json.loads(content)
            if document.get('type')!='FeatureCollection' or not document.get('features'): raise ValueError('Expected a nonempty FeatureCollection')
            ids=[]
            for feature in document['features']:
                geom=shape(feature['geometry'])
                if not geom.is_valid or geom.is_empty or geom.geom_type not in ('Polygon','MultiPolygon'): raise ValueError('Invalid polygon geometry')
                x1,y1,x2,y2=geom.bounds
                if not (-180<=x1<=x2<=180 and -90<=y1<=y2<=90): raise ValueError('Expected WGS84 longitude and latitude')
                ids.append(str(feature['properties']['city_id']))
            if len(ids)!=len(set(ids)): raise ValueError('Duplicate city identifiers')
            if not set(ids).issubset({x['city_id'] for x in cities()}): raise ValueError('Unmatched geographic identifiers')
            return result(dict(rows=len(ids),cities_detected=ids,valid=True,saved=False,sha256=hashlib.sha256(content).hexdigest()),'upload-preview')
        raise ValueError('Only CSV and GeoJSON are supported')
    except (ValueError,KeyError,TypeError): raise HTTPException(422,'Invalid dataset. Check columns, city identifiers, coordinates, and file format.')

@app.post('/api/import/commit',response_model=Envelope)
async def commit(file:UploadFile=File(...),expected_sha256:str=Form(...),x_admin_token:str|None=Header(None)):
    report=await preview(file,x_admin_token)
    if not report.data['valid']: raise HTTPException(422,'Invalid observations must be corrected before saving.')
    if not secrets.compare_digest(expected_sha256,report.data['sha256']): raise HTTPException(409,'The file changed after preview. Validate it again.')
    await file.seek(0)
    content=await file.read(5_000_001)
    candidate_id=str(uuid.uuid4())
    folder=DATA/'candidates';folder.mkdir(exist_ok=True)
    suffix='.csv' if file.filename.lower().endswith('.csv') else '.geojson'
    (folder/(candidate_id+suffix)).write_bytes(content)
    (folder/(candidate_id+'.metadata.json')).write_text(json.dumps(dict(candidate_id=candidate_id,status='pending-review',provenance='unverified-upload',report=report.data)))
    return result(dict(candidate_id=candidate_id,saved=True,active=False),'unverified-upload')


