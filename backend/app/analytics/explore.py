import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr, linregress
from app.services.data import observations, cities, records
from app.analytics.heat import exposure_index, risk

def analytics():
    df=observations().copy()
    columns=['temperature','humidity','heat_index']
    distribution=df[columns].describe(percentiles=[.05,.25,.5,.75,.95]).round(3)
    hourly=df.groupby(df.timestamp.dt.hour)[columns].mean()
    monthly=df.groupby(df.timestamp.dt.strftime('%Y-%m'))[columns].mean()
    city=df.groupby('city_id').agg(temperature=('temperature','mean'),humidity=('humidity','mean'),heat_index=('heat_index','mean'),peak=('heat_index','max'),n=('heat_index','size')).reset_index().merge(pd.DataFrame(cities()),on='city_id')
    city['exposure_index']=exposure_index(city.heat_index,city.population_density,city.vegetation,city.built_up)
    city['risk']=city.exposure_index.map(risk)
    city['elevated_frequency']=0.0
    city['trend']=0.0
    for idx,row in city.iterrows():
        values=df[df.city_id==row.city_id].sort_values('timestamp')
        scores=exposure_index(values.heat_index,row.population_density,row.vegetation,row.built_up)
        city.loc[idx,'elevated_frequency']=float(np.mean(scores>=50)*100)
        city.loc[idx,'trend']=float(values.tail(168).heat_index.mean()-values.iloc[-336:-168].heat_index.mean())
    correlations=[]
    # Independent cities, not duplicated hourly static covariates.
    for x,y in [('vegetation','temperature'),('population_density','heat_index'),('built_up','exposure_index')]:
        if city[x].isna().any() or city[y].isna().any():continue
        p=pearsonr(city[x],city[y]);s=spearmanr(city[x],city[y])
        correlations.append(dict(x=x,y=y,pearson=float(p.statistic),spearman=float(s.statistic),p_value=float(p.pvalue),n=len(city),unit='city-level annual mean'))
    daily=df.groupby(df.timestamp.dt.strftime('%Y-%m-%d'))[columns].mean()
    regression=linregress(np.arange(len(daily)),daily.heat_index)
    return dict(distributions=distribution.reset_index().rename(columns={'index':'statistic'}).to_dict('records'),
        hourly=records(hourly.reset_index().rename(columns={'timestamp':'hour'})),monthly=records(monthly.reset_index().rename(columns={'timestamp':'month'})),
        daily=records(daily.reset_index().rename(columns={'timestamp':'date'})),city_stats=records(city),correlations=correlations,
        summary=dict(highest=float(df.heat_index.max()),mean=float(df.heat_index.mean()),peak_hour=int(hourly.heat_index.idxmax()),peak_month=monthly.heat_index.idxmax(),slope_per_day=float(regression.slope),n_days=len(daily),trend_note='Descriptive OLS slope only; seasonality and autocorrelation prevent a causal or long-term warming interpretation.'))

