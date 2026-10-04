import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG = json.loads((ROOT / 'config' / 'methodology.json').read_text(encoding='utf-8-sig'))
DATA = ROOT / 'backend' / 'data' / CONFIG.get('data_directory','')

