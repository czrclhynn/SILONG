import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import CONFIG,DATA
from app.services.data import cities,observations,records

def main():
    df=observations()
    # Compact tuples retain all hourly observations; the frontend decodes once.
    tuples=[[t.isoformat(),c,float(a),float(h),float(i)] for t,c,a,h,i in df[['timestamp','city_id','temperature','humidity','heat_index']].itertuples(index=False,name=None)]
    bundle=dict(cities=cities(),observation_columns=['timestamp','city_id','temperature','humidity','heat_index'],observations=tuples,
        config=CONFIG,quality=json.loads((DATA/'quality.json').read_text(encoding='utf-8-sig')),daily=[],monthly=[],hourly=[],city_stats=[],correlations=[],distributions=[])
    forecast=DATA/'forecasts.json'
    from app.analytics.explore import analytics
    bundle.update(analytics())
    if forecast.exists(): bundle['forecasts']=json.loads(forecast.read_text(encoding='utf-8-sig'))
    source=DATA/'manifest.json'
    if source.exists():bundle['sources']=json.loads(source.read_text(encoding='utf-8-sig'))
    target=ROOT/'frontend/public/data/dataset.json'
    target.write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False),encoding='utf-8')
    print(f'Exported active dataset bundle: {target.stat().st_size/1e6:.1f} MB')
if __name__=='__main__': main()


