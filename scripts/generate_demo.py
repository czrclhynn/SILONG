"""Recreate deterministic synthetic weather and demographic inputs; no real measurements."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import numpy as np
import pandas as pd
from app.core.config import DATA, ROOT, CONFIG
from app.analytics.heat import heat_index, exposure_index, risk
from app.pipeline.cleaning import clean_observations

# Optional demonstration recreation is isolated from the active real-data directory.
DATA = ROOT / 'backend' / 'data' / 'demo'
CONFIG = json.loads((ROOT/'config/methodology.demo.json').read_text(encoding='utf-8-sig'))

NAMES = ['Caloocan','Las Piñas','Makati','Malabon','Mandaluyong','Manila','Marikina','Muntinlupa','Navotas','Parañaque','Pasay','Pasig','Pateros','Quezon City','San Juan','Taguig','Valenzuela']

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    boundaries = json.loads((ROOT/'backend/data/boundaries.geojson').read_text(encoding='utf-8-sig'))
    cities = []
    for i, feature in enumerate(sorted(boundaries['features'], key=lambda f: f['properties']['name'])):
        p = feature['properties']
        # All these demographic/environmental values are invented, not census values.
        cities.append(dict(city_id=p['city_id'], name=p['name'], population=int(rng.integers(90000,1900000)),
            population_density=int(rng.integers(7000,42000)), vegetation=round(float(rng.uniform(8,36)),1),
            built_up=round(float(rng.uniform(55,88)),1), provenance='synthetic'))
        # Consistent synthetic residential count = reference city area × synthetic density.
        cities[-1]['area_km2']=p['area_km2']
        cities[-1]['population']=round(p['area_km2']*cities[-1]['population_density'])
    times = pd.date_range('2025-10-01', '2026-09-30 23:00', freq='h', tz='Asia/Manila')
    frames=[]
    regional_noise = np.zeros(len(times))
    for k in range(1,len(times)):
        regional_noise[k] = .85*regional_noise[k-1] + rng.normal(0,.3)
    for city in cities:
        hour = times.hour.to_numpy()
        season = 1.7*np.cos(2*np.pi*(times.dayofyear.to_numpy()-125)/365.25)
        offset = rng.uniform(-.7,.9)
        temp = 29.6 + season + 3.2*np.cos(2*np.pi*(hour-14)/24) + offset + regional_noise + rng.normal(0,.3,len(times))
        humidity = np.clip(75 - 10*np.cos(2*np.pi*(hour-14)/24) - 2*season + rng.normal(0,2,len(times)),40,98)
        frames.append(pd.DataFrame(dict(timestamp=times,city_id=city['city_id'],temperature=np.round(temp,2),humidity=np.round(humidity,2))))
    raw=pd.concat(frames,ignore_index=True)
    raw.to_csv(DATA/'observations.csv',index=False)
    clean,quality=clean_observations(raw,{x['city_id'] for x in cities})
    clean['heat_index']=heat_index(clean.temperature,clean.humidity).round(2)
    clean['source_heat_index']=None
    clean['provenance']='synthetic'
    clean.to_csv(DATA/'clean.csv',index=False)
    (DATA/'cities.json').write_text(json.dumps(cities,indent=2),encoding='utf-8')
    quality.update(dataset_version=CONFIG['version'],last_dataset_update=str(times[-1]),expected_records=len(times)*len(cities),coverage_percent=100)
    (DATA/'quality.json').write_text(json.dumps(quality,indent=2),encoding='utf-8')
    print(f'Created {len(clean):,} synthetic hourly rows for {len(cities)} cities.')

if __name__=='__main__': main()

