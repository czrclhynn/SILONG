export type City={city_id:string;name:string;population:number;population_density:number;vegetation:number;built_up:number;provenance:string};
export type Row=City&{timestamp:string;temperature:number;humidity:number;heat_index:number;exposure_index:number;risk:string;exposed_population:number;source_heat_index:number|null};
export type Observation={timestamp:string;city_id:string;temperature:number;humidity:number;heat_index:number};
export type Threshold={label:string;min:number;color:string};
export type Config={version:string;dataset_label:string;weights:Record<string,number>;normalization:Record<string,number[]>;risk_thresholds:Threshold[];elevated_min:number;weight_rationale:string;exposure_method:string;heat_index_method:string;heat_index_source:string;simulation_method:string;limitations:string[]};
export type Bundle={cities:City[];observations:Observation[];config:Config;quality:Record<string,string|number>;daily:Record<string,unknown>[];monthly:Record<string,unknown>[];hourly:Record<string,unknown>[];city_stats:Record<string,unknown>[];correlations:Record<string,unknown>[];distributions:Record<string,unknown>[];forecasts?:ForecastBundle};
export type ForecastBundle={registry:{selected:string;version:string;trained_at:string;dataset_version:string;features:string[];validation_period:string;test_period:string;metrics:{model:string;mae:number;rmse:number;r2:number;accuracy:number;precision:number;recall:number;f1:number}[];feature_importance:{feature:string;importance:number}[];horizon_metrics:{horizon:number;mae:number;rmse:number;coverage:number}[]};predictions:{city_id:string;horizon:number;timestamp:string;heat_index:number;lower:number;upper:number;risk:string}[]};

export function decodeBundle(data:Bundle & {observations:unknown[]}):Bundle {
  return {...data,cities:data.cities.map(c=>({...c,vegetation:typeof c.vegetation==='number'?c.vegetation:NaN,built_up:typeof c.built_up==='number'?c.built_up:NaN})),
    city_stats:data.city_stats.map(c=>({...c,vegetation:typeof c.vegetation==='number'?c.vegetation:NaN,built_up:typeof c.built_up==='number'?c.built_up:NaN})),
    observations:(data.observations as unknown as [string,string,number,number,number][]).map(r=>({timestamp:r[0],city_id:r[1],temperature:r[2],humidity:r[3],heat_index:r[4]}))};
}
