"""Direct multi-horizon models; fit on train, select/calibrate on validation, report untouched test."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor,GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score,accuracy_score,precision_recall_fscore_support
from sklearn.inspection import permutation_importance
from app.services.data import observations,cities
from app.ml.features import FEATURES,engineer,supervised
from app.analytics.heat import exposure_index,risk
from app.core.config import DATA,CONFIG

def metrics(y,p):
    return dict(mae=float(mean_absolute_error(y,p)),rmse=float(np.sqrt(mean_squared_error(y,p))),r2=float(r2_score(y,p)))

def main():
    df=observations();trained={};validation={};splits={}
    cuts=[pd.Timestamp(t,tz='Asia/Manila') for t in CONFIG.get('model_split_dates',['2026-07-01','2026-09-01'])]
    for horizon in [6,12,24]:
        data=supervised(df,horizon)
        train=data[data.target_time<cuts[0]].iloc[::6]
        valid=data[(data.timestamp>=cuts[0])&(data.target_time<cuts[1])].iloc[::6]
        test=data[data.timestamp>=cuts[1]].iloc[::6]
        splits[horizon]=(train,valid,test)
        candidates={'Persistence':None,'Linear regression':LinearRegression(),'Random forest':RandomForestRegressor(n_estimators=60,max_depth=14,min_samples_leaf=5,random_state=2026,n_jobs=2),'Gradient boosting':GradientBoostingRegressor(n_estimators=90,max_depth=3,learning_rate=.07,random_state=2026)}
        trained[horizon]={};validation[horizon]={}
        for name,model in candidates.items():
            if model is not None:model.fit(train[FEATURES],train.target)
            pred=valid.heat_index.to_numpy() if model is None else model.predict(valid[FEATURES])
            trained[horizon][name]=model
            validation[horizon][name]=metrics(valid.target,pred)
        print(f'{horizon}h: trained {len(train)} rows, validated {len(valid)}, held out {len(test)}',flush=True)
    names=list(validation[6]);selected=min(names,key=lambda n:np.mean([validation[h][n]['mae'] for h in validation]))
    city_lookup={c['city_id']:c for c in cities()}
    table=[]
    for name in names:
        _,_,test=splits[6];model=trained[6][name]
        p=test.heat_index.to_numpy() if model is None else model.predict(test[FEATURES])
        actual=[];predicted=[]
        for c,y,yp in zip(test.city_id,test.target,p):
            city=city_lookup[c]
            actual.append(risk(float(exposure_index(y,city['population_density'],city['vegetation'],city['built_up']))))
            predicted.append(risk(float(exposure_index(yp,city['population_density'],city['vegetation'],city['built_up']))))
        precision,recall,f1,_=precision_recall_fscore_support(actual,predicted,average='macro',zero_division=0)
        table.append(dict(model=name,**metrics(test.target,p),accuracy=float(accuracy_score(actual,predicted)),precision=float(precision),recall=float(recall),f1=float(f1)))
    latest=engineer(df).groupby('city_id').tail(1)
    forecasts=[];horizon_metrics=[];artifacts={}
    for h in [6,12,24]:
        train,valid,test=splits[h];model=trained[h][selected]
        predict=lambda frame:frame.heat_index.to_numpy() if model is None else model.predict(frame[FEATURES])
        width=float(np.quantile(np.abs(valid.target-predict(valid)),.9))
        yp=predict(test)
        horizon_metrics.append(dict(horizon=h,**metrics(test.target,yp),coverage=float(np.mean(np.abs(test.target-yp)<=width)),n_test=len(test),interval_half_width=width))
        artifacts[h]=dict(model=model,interval_half_width=width)
        for (_,row),p in zip(latest.iterrows(),predict(latest)):
            c=city_lookup[row.city_id]
            forecasts.append(dict(city_id=row.city_id,horizon=h,timestamp=(row.timestamp+pd.Timedelta(hours=h)).isoformat(),heat_index=float(p),lower=float(p-width),upper=float(p+width),risk=risk(float(exposure_index(p,c['population_density'],c['vegetation'],c['built_up'])))))
    importance=[]
    model=trained[6][selected]
    if model is not None:
        sample=splits[6][1].iloc[::8]
        perm=permutation_importance(model,sample[FEATURES],sample.target,n_repeats=3,random_state=2026,scoring='neg_mean_absolute_error')
        importance=sorted([dict(feature=f,importance=float(v)) for f,v in zip(FEATURES,perm.importances_mean)],key=lambda x:x['importance'],reverse=True)
    registry=dict(selected=selected,version='silong-direct-v1',trained_at=datetime.now(timezone.utc).isoformat(),dataset_version=CONFIG['version'],features=FEATURES,validation_period='2026-07-01 to 2026-08-31',test_period='2026-09-01 to 2026-09-30',train_period='2025-10-01 to 2026-06-30',metrics=table,validation_metrics=validation,feature_importance=importance,horizon_metrics=horizon_metrics,selection='Lowest mean validation MAE across 6, 12, 24 hours. Models trained only on training period. Test set is never used for model selection.',interval_method='Symmetric 90th percentile of absolute validation residuals per horizon; empirical, not calibrated real-world confidence. Coverage is measured on the held-out test set.',issue_time=str(latest.timestamp.max()),sampling='Every sixth training/validation/test row within time-ordered city series; no shuffle.')
    registry.update(train_period=f'{df.timestamp.min().date()} to {(cuts[0]-pd.Timedelta(days=1)).date()}',validation_period=f'{cuts[0].date()} to {(cuts[1]-pd.Timedelta(days=1)).date()}',test_period=f'{cuts[1].date()} to {df.timestamp.max().date()}',provenance=CONFIG.get('provenance','synthetic'))
    (DATA/'forecasts.json').write_text(json.dumps(dict(registry=registry,predictions=forecasts),indent=2,allow_nan=False),encoding='utf-8')
    output=ROOT/'backend/artifacts';output.mkdir(exist_ok=True)
    joblib.dump(dict(registry=registry,models=artifacts,features=FEATURES),output/(CONFIG['version']+'.joblib'))
    print(f'Selected {selected}. Saved model artifact, test metrics, intervals and forecast demo.',flush=True)
if __name__=='__main__':main()

