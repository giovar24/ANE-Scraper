import json
from pathlib import Path

Path("checkpoints/state.json").write_text(
    json.dumps({"fase": "listado", "siguiente_pagina": 1, "total_puestos": None}),
    encoding="utf-8",
)
print("state reseteado")
