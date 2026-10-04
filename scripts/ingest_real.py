"""Download and cache Open-Meteo ERA5-Land, then join verified historical PSA counts.
No synthetic fallback; a failed or incomplete download aborts activation.
"""
import sys,json,urllib.request,urllib.parse,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import pandas as pd
from shapely.geometry import shape
from app.pipeline.cleaning import clean_observations
from app.analytics.heat import heat_index

def main():
    target=ROOT/'backend/data/real';target.mkdir(exist_ok=True)
    geo=json.loads((ROOT/'backend/data/boundaries.geojson').read_text(encoding='utf-8-sig'))
    features=sorted(geo['features'],key=lambda f:f['properties']['name'])
    points=[shape(f['geometry']).representative_point() for f in features]
    query=dict(latitude=','.join(f'{p.y:.5f}' for p in points),longitude=','.join(f'{p.x:.5f}' for p in points),start_date='2025-01-01',end_date='2025-12-31',hourly='temperature_2m,relative_humidity_2m',models='era5_land',timezone='Asia/Manila')
    url='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode(query)
    raw_path=target/'open-meteo-era5-land-2025.json'
    if not raw_path.exists():
        request=urllib.request.Request(url,headers={'User-Agent':'SILONG research dataset importer/1.0'})
        with urllib.request.urlopen(request,timeout=180) as response: content=response.read()
        payload=json.loads(content)
        if not isinstance(payload,list) or len(payload)!=17:raise ValueError('Expected 17 location responses; refusing partial activation')
        raw_path.write_bytes(content)
    payload=json.loads(raw_path.read_text(encoding='utf-8-sig'))
    census=json.loads((ROOT/'backend/data/census-2020.json').read_text(encoding='utf-8-sig'))
    assert sum(census['populations'].values())==census['expected_ncr_total']
    cities=[];frames=[];grids=set()
    for f,p,weather in zip(features,points,payload):
        props=f['properties'];hourly=weather['hourly'];units=weather['hourly_units']
        assert units['temperature_2m']=='°C' and units['relative_humidity_2m']=='%'
        assert weather['utc_offset_seconds']==28800
        assert len(hourly['time'])==8760
        city_id=props['city_id'];name=props['name'];population=census['populations'][name]
        grid=(weather['latitude'],weather['longitude']);grids.add(grid)
        cities.append(dict(city_id=city_id,name=name,population=population,population_density=round(population/props['area_km2']),area_km2=props['area_km2'],vegetation=None,built_up=None,provenance='PSA 2020 census + ERA5-Land reanalysis',population_year=2020,sample_latitude=p.y,sample_longitude=p.x,weather_grid_latitude=grid[0],weather_grid_longitude=grid[1]))
        frames.append(pd.DataFrame(dict(timestamp=hourly['time'],city_id=city_id,temperature=hourly['temperature_2m'],humidity=hourly['relative_humidity_2m'])))
    raw=pd.concat(frames,ignore_index=True)
    clean,quality=clean_observations(raw,{c['city_id'] for c in cities})
    if quality['invalid_observations'] or len(clean)!=148920:raise ValueError('Missing or invalid weather; inspect before activation')
    clean['heat_index']=heat_index(clean.temperature,clean.humidity).round(2)
    clean['source_heat_index']=None;clean['provenance']='reanalysis'
    raw.to_csv(target/'observations.csv',index=False);clean.to_csv(target/'clean.csv',index=False)
    (target/'cities.json').write_text(json.dumps(cities,indent=2),encoding='utf-8')
    fetched=datetime.now(timezone.utc).isoformat()
    quality.update(dataset_version='era5land-2025-psa2020-v1',expected_records=148920,coverage_percent=100,last_dataset_update=fetched,source_start='2025-01-01',source_end='2025-12-31',unique_weather_grid_points=len(grids),population_census_year=2020)
    (target/'quality.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    manifest=dict(version=quality['dataset_version'],provenance='reanalysis',fetched_at=fetched,source_url=url,weather_provider='Open-Meteo / Copernicus ERA5-Land',weather_license='CC BY 4.0',weather_resolution='0.1 degree (~11 km); downscaled point samples, not citywide station observations',raw_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),population_source=census,unique_grid_points=len(grids),environmental_data='Not available; never filled with synthetic values')
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Validated {len(clean):,} real reanalysis records, {len(grids)} distinct returned grid points, and PSA census total {sum(c["population"] for c in cities):,}.',flush=True)
if __name__=='__main__':main()

