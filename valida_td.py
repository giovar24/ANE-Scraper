"""Prueba: TYPED-DECISIONS (3 campos) vs el de 10 campos, sobre las mismas 40 filas."""
import csv
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import laya  # noqa: E402

random.seed(42)
filas = list(csv.DictReader(open("salida/puestos.csv", encoding="utf-8-sig")))
muestra = random.sample(filas, 40)

P = {
    "teletrabajo": {"type": "choice",
                    "instructions": "Dice el texto que el trabajo es teletrabajo o remoto?",
                    "criteria": {"A": "si lo dice", "B": "no lo dice"}},
    "licencia": {"type": "choice",
                 "instructions": "Pide el texto licencia de conducir?",
                 "criteria": {"A": "si pide", "B": "no pide"}},
}


def gt(f):
    txt = " ".join([f.get("titulo", ""), f.get("jornada", ""), f.get("descripcion", ""),
                    f.get("requisitos", ""), f.get("habilidades", "")]).lower()
    a = "A" if re.search(r"teletrabajo|remoto|desde casa|home office", txt) else "B"
    lic = bool(re.search(r"licen[cs]i[ae]|lic\.?\s*[bdc]\d|\bb[123]\b", txt)) \
        and not re.search(r"sin licencia", txt)
    return {"teletrabajo": a, "licencia": "A" if lic else "B"}


agent = laya.load("convaiinnovations/laya", subfolder="typed-decisions")
ok = {"teletrabajo": 0, "licencia": 0}
for f in muestra:
    estado = f"Puesto: {f['titulo']}\nDescripcion: {f['descripcion']}\nRequisitos: {f['requisitos']}"
    g = gt(f)
    r = agent.predict(estado, P, max_len=8192)
    for q in ok:
        if r["answers"][q]["choice"] == g[q]:
            ok[q] += 1
print("TYPED-DECISIONS (3 campos):", ok, "/40")

