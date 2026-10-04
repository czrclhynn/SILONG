import geopandas as gpd
import json
from pathlib import Path

def join_locations(boundary_path, table):
    # GeoJSON can be decoded directly; GDAL is not required for this format.
    document=json.loads(Path(boundary_path).read_text(encoding='utf-8-sig'))
    if 'crs' in document:
        raise ValueError('Supply RFC 7946 GeoJSON in WGS84, without a legacy CRS override')
    boundaries = gpd.GeoDataFrame.from_features(document['features'])
    # RFC 7946 explicitly fixes GeoJSON to WGS84. This join does not project coordinates
    # or calculate areas, so it needs neither GDAL nor a projection DLL.
    bounds=boundaries.total_bounds
    if not (-180<=bounds[0]<=bounds[2]<=180 and -90<=bounds[1]<=bounds[3]<=90):
        raise ValueError('Coordinates outside WGS84 longitude/latitude bounds')
    if not boundaries.geometry.is_valid.all() or boundaries.city_id.duplicated().any():
        raise ValueError('Invalid geometry or duplicate geographic identifiers')
    if not set(table.city_id).issubset(set(boundaries.city_id)):
        raise ValueError('Unmatched geographic identifiers')
    result=boundaries.merge(table, on='city_id', validate='one_to_many')
    result.attrs['coordinate_reference']='EPSG:4326 (RFC 7946)'
    return result

