"""Validación: compara Laya vs reglas deterministas sobre filas reales del CSV.

Ground truth aproximado por palabras clave (para teletrabajo, licencia,
tiempo completo y años de experiencia). Mide la precisión real de Laya
sobre nuestros datos antes de analizar los 1.984.
"""
import csv
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import laya  # noqa: E402

random.seed(42)
filas = list(csv.DictReader(open("salida/puestos.csv", encoding="utf-8-sig")))
muestra = random.sample(filas, 40)

PREGUNTAS = {
    "teletrabajo": {
        "type": "choice",
        "instructions": "Lee el texto del puesto. ¿Dice en alguna parte que el trabajo sea "
                        "teletrabajo, remoto o desde casa? Responde solo segun el texto.",
        "criteria": {
            "A": "el texto dice que es teletrabajo o remoto",
            "B": "el texto no dice eso",
        },
    },
    "licencia": {
        "type": "choice",
        "instructions": "Lee el texto del puesto. ¿Pide licencia de conducir (B1, B2, B3, C2, "
                        "D3, profesional, etc.)? Responde solo segun el texto.",
        "criteria": {
            "A": "el texto pide licencia de conducir",
            "B": "el texto no pide licencia",
        },
    },
    "jornada_tiempo_completo": {
        "type": "choice",
        "instructions": "Lee el texto del puesto. ¿Dice que la jornada es tiempo completo? "
                        "Responde solo segun el texto.",
        "criteria": {"A": "el texto dice tiempo completo", "B": "no lo dice"},
    },
}


def ground_truth(f: dict) -> dict:
    txt = " ".join([f.get("titulo", ""), f.get("jornada", ""), f.get("descripcion", ""),
                    f.get("requisitos", ""), f.get("habilidades", ""),
                    f.get("tipo_contratacion", "")]).lower()
    gt = {}
    gt["teletrabajo"] = "A" if re.search(r"teletrabajo|remoto|desde casa|home\s*office", txt) else "B"
    # abreviaturas: "Lic B1", "lic. C2", "categoria B2 y B3", "licencia profesional"
    pide_lic = bool(re.search(
        r"licen[cs]i[ae]|lic\.?\s*[bdc]\d|\bb[123]\b|\bc2\b|\bd3\b|categoria\s+[bdc]\d", txt))
    if re.search(r"sin licencia|no requiere licencia", txt):
        pide_lic = False
    gt["licencia"] = "A" if pide_lic else "B"
    gt["jornada_tiempo_completo"] = "A" if re.search(r"tiempo completo", txt) else "B"
    return gt


def texto(f: dict) -> str:
    partes = [f"Titulo: {f['titulo']}", f"Empresa: {f['empresa']}"]
    for k in ("jornada", "salario", "nivel_academico", "experiencia",
              "tipo_contratacion", "descripcion", "requisitos", "habilidades"):
        if f.get(k):
            partes.append(f"{k}: {f[k]}")
    return "\n".join(partes)


agent = laya.load("convaiinnovations/laya", subfolder="multilingual")

aciertos = {"teletrabajo": 0, "licencia": 0, "jornada_tiempo_completo": 0}
ignorados = {"teletrabajo": 0, "licencia": 0, "jornada_tiempo_completo": 0}
fallos = []

for f in muestra:
    gt = ground_truth(f)
    res = agent.predict(texto(f), PREGUNTAS, max_len=8192)
    for q in aciertos:
        pred = res["answers"][q]["choice"]
        if gt[q] == pred:
            aciertos[q] += 1
        else:
            if len(fallos) < 12:
                fallos.append((q, f["titulo"][:40], gt[q], pred,
                               res["answers"][q]["probabilities"]))

print("\n--- RESULTADOS (40 filas reales) ---")
for q, ok in aciertos.items():
    print(f"{q:26} {ok}/40 = {ok/40:.0%}")
print("\nEjemplos de fallo (campo, puesto, gt, pred, probs):")
for x in fallos[:12]:
    print("  ", x)
