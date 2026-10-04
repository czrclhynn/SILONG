import numpy as np
from app.core.config import CONFIG


def heat_index(temperature, humidity):
    """NWS algorithm; input Celsius and percent RH, output Celsius."""
    t = np.asarray(temperature, dtype=float) * 9 / 5 + 32
    r = np.asarray(humidity, dtype=float)
    if np.any(~np.isfinite(t)) or np.any(~np.isfinite(r)) or np.any((r < 0) | (r > 100)):
        raise ValueError('Finite temperature and humidity in [0, 100] required')
    simple = 0.5 * (t + 61 + (t - 68) * 1.2 + r * 0.094)
    regression = (-42.379 + 2.04901523*t + 10.14333127*r - .22475541*t*r
                  - .00683783*t*t - .05481717*r*r + .00122874*t*t*r
                  + .00085282*t*r*r - .00000199*t*t*r*r)
    low = ((13-r)/4) * np.sqrt(np.maximum(0, (17-np.abs(t-95))/17))
    high = ((r-85)/10) * ((87-t)/5)
    regression = regression - np.where((r<13)&(t>=80)&(t<=112), low, 0)
    regression = regression + np.where((r>85)&(t>=80)&(t<=87), high, 0)
    result = (np.where((simple+t)/2 >= 80, regression, simple)-32)*5/9
    return result


def exposure_index(hi, density, vegetation, built_up):
    values = dict(heat=hi, population_density=density, built_up=built_up,
                  vegetation_deficit=100-np.asarray(vegetation) if CONFIG['weights']['vegetation_deficit']>0 else 0)
    return sum(CONFIG['weights'][k] * np.clip((np.asarray(v)-CONFIG['normalization'][k][0]) /
               (CONFIG['normalization'][k][1]-CONFIG['normalization'][k][0]), 0, 1) * 100
               for k, v in values.items() if CONFIG['weights'][k]>0)


def risk(score):
    return next(x['label'] for x in reversed(CONFIG['risk_thresholds']) if score >= x['min'])

