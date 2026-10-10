"""Sonda: descubre la estructura exacta de resultados de Laya con nuestras preguntas."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import laya  # noqa: E402

preguntas = json.loads(Path("preguntas.json").read_text(encoding="utf-8"))
state = {
    "titulo": "Auxiliar de Bodega",
    "empresa": "Empresa X",
    "ubicacion": "San Jose / San Jose",
    "jornada": "Tiempo completo (Jornada diurna)",
    "salario": "\u20a1390000 - \u20a1390000",
    "descripcion": "Experiencia en control de inventario, entrada y salida de mercaderia. Residir en el area de San Jose. Disponibilidad inmediata.",
}

print("cargando modelo (primera vez descarga pesos)...")
agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
res = agent.predict(state, preguntas["preguntas"], max_len=8192)

Path("checkpoints/laya_probe.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
)
print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
