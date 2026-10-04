"""Optional PostGIS seed, safe upsert limited to the synthetic dataset version."""
import sys,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import pandas as pd
from sqlalchemy import create_engine,text
from app.core.config import DATA,CONFIG

def main():
    url=os.environ.get('DATABASE_URL')
    if not url: raise SystemExit('Set DATABASE_URL to your PostgreSQL/PostGIS database.')
    engine=create_engine(url)
    boundary=json.loads((DATA/'boundaries.geojson').read_text(encoding='utf-8-sig'))
    df=pd.read_csv(DATA/'clean.csv',dtype={'city_id':str})
    with engine.begin() as connection:
        # Execute the reviewed schema migration before loading any rows.
        for statement in (ROOT/'database/migrations/001_initial.sql').read_text(encoding='utf-8-sig').split(';'):
            if statement.strip():connection.execute(text(statement))
        connection.execute(text("INSERT INTO datasets(id,provenance,quality) VALUES (:id,:provenance,CAST(:quality AS jsonb)) ON CONFLICT (id) DO UPDATE SET quality=EXCLUDED.quality"),dict(id=CONFIG['version'],provenance=CONFIG.get('provenance','synthetic'),quality=(DATA/'quality.json').read_text(encoding='utf-8-sig')))
        for f in boundary['features']:
            connection.execute(text('INSERT INTO locations(city_id,name,boundary) VALUES (:id,:name,ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geo),4326))) ON CONFLICT (city_id) DO NOTHING'),dict(id=f['properties']['city_id'],name=f['properties']['name'],geo=json.dumps(f['geometry'])))
        query=text('INSERT INTO observations(dataset_id,city_id,timestamp,temperature,humidity,heat_index,source_heat_index,outlier_flag) VALUES (:dataset_id,:city_id,:timestamp,:temperature,:humidity,:heat_index,:source_heat_index,:outlier_flag) ON CONFLICT (dataset_id,city_id,timestamp) DO NOTHING')
        rows=df.assign(dataset_id=CONFIG['version']).where(pd.notna(df),None).to_dict('records')
        for row in rows:row['source_heat_index']=None
        for i in range(0,len(rows),5000):connection.execute(query,rows[i:i+5000])
    print(f'Seeded {len(df):,} active dataset records and 17 reference geometries.')
if __name__=='__main__':main()


