import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
features=[]
for path in sorted((ROOT/'backend/data/raw').glob('*.json')):
    for f in json.loads(path.read_text(encoding='utf-8-sig'))['features']:
        p=f['properties']
        name=p['adm3_en'].replace('City of ','')
        if name!='Quezon City': name=name.removesuffix(' City')
        f['properties']={'city_id':str(p['adm3_psgc']),'name':name,'area_km2':p['area_crs']/1e6,'boundary_vintage':2023,'source':'faeldon/philippines-json-maps (MIT)'}
        features.append(f)
assert len(features)==17 and len({f['properties']['city_id'] for f in features})==17
output=json.dumps({'type':'FeatureCollection','features':features},separators=(',',':'),ensure_ascii=False)
(ROOT/'backend/data/boundaries.geojson').write_text(output,encoding='utf-8')
(ROOT/'frontend/public/data').mkdir(parents=True,exist_ok=True)
(ROOT/'frontend/public/data/boundaries.geojson').write_text(output,encoding='utf-8')
print('Prepared 17 NCR city geometries with source PSGC identifiers.')

