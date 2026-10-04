import pandas as pd
import numpy as np

REQUIRED = ['timestamp', 'city_id', 'temperature', 'humidity']


def clean_observations(raw: pd.DataFrame, city_ids: set):
    missing_columns = sorted(set(REQUIRED)-set(raw.columns))
    if missing_columns:
        raise ValueError('Missing required columns: ' + ', '.join(missing_columns))
    df = raw.copy()
    stats = {'records_processed': len(df), 'missing_values': int(df[REQUIRED].isna().sum().sum())}
    df['city_id'] = df.city_id.astype(str).str.strip()
    # Naive input timestamps are interpreted in Manila, never silently as UTC.
    def parse(value):
        try:
            t = pd.Timestamp(value)
            if pd.isna(t): return pd.NaT
            return t.tz_localize('Asia/Manila') if t.tzinfo is None else t.tz_convert('Asia/Manila')
        except (ValueError, TypeError): return pd.NaT
    df['timestamp'] = pd.to_datetime(df.timestamp.map(parse), utc=True).dt.tz_convert('Asia/Manila')
    for col in ['temperature', 'humidity']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    valid = df.timestamp.notna() & df.city_id.isin(city_ids) & df.temperature.between(10, 50) & df.humidity.between(0,100)
    stats['invalid_observations'] = int((~valid).sum())
    df = df[valid].copy()
    stats['duplicates_removed'] = int(df.duplicated(['city_id','timestamp']).sum())
    df = df.drop_duplicates(['city_id','timestamp'], keep='last').sort_values(['city_id','timestamp'])
    # Retain plausible extremes; flag robust outliers rather than censor heat events.
    median = df.groupby('city_id').temperature.transform('median')
    mad = (df.temperature-median).abs().groupby(df.city_id).transform('median')
    df['outlier_flag'] = ((df.temperature-median).abs() > 6*mad.clip(lower=.1))
    stats['outliers_flagged'] = int(df.outlier_flag.sum())
    stats['records_retained'] = len(df)
    stats['missing_policy'] = 'Reject missing required measurements; no interpolation or backfill.'
    return df, stats

