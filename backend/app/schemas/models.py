from pydantic import BaseModel, Field
from typing import Any, Literal
from app.core.config import CONFIG

class Envelope(BaseModel):
    provenance: str = CONFIG.get('provenance','synthetic')
    dataset_version: str = CONFIG['version']
    data: Any

class SimulationInput(BaseModel):
    city_id: str
    date: str = CONFIG.get('end_date','2026-09-30')
    hour: int = Field(14,ge=0,le=23)
    temperature_change: float = Field(0,ge=-3,le=5)
    humidity_change: float = Field(0,ge=-20,le=20)
    vegetation_change: float = Field(0,ge=0,le=50)
    density_change: float = Field(0,ge=-20,le=30)
    built_up: Literal['baseline','low','medium','high'] = 'baseline'

