from typing import Protocol
from pathlib import Path
import pandas as pd

class ObservationAdapter(Protocol):
    def read(self) -> pd.DataFrame: ...

class CSVAdapter:
    def __init__(self, path: Path, aliases: dict | None = None):
        self.path, self.aliases = path, aliases or {}
    def read(self):
        df = pd.read_csv(self.path, dtype={'city_id': str})
        if 'city_id' in df:
            df['city_id'] = df.city_id.str.strip().replace(self.aliases)
        return df

class SatelliteAdapter:
    def read(self):
        raise NotImplementedError('No satellite dataset configured. Supply licensed NDVI/LST rasters with acquisition dates and CRS.')

