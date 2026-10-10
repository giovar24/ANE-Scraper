"""F6: analiza salida/puestos.csv con Laya (modelo de decisiones local) -> salida/puestos_analizados.csv

Cada fila pasa a Laya con las preguntas tipadas de preguntas.json (tipo choice / score).
Laya NO genera texto: devuelve la respuesta del catálogo del usuario + probabilidades.

Reanudable: checkpoints/analisis.jsonl guarda lo ya analizado (por id).
"""
import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from laya import Router  # noqa: E402

ENTRADA = Path("salida/puestos.csv")
SALIDA = Path("salida/puestos_analizados.csv")
PREGUNTAS = Path("preguntas.json")
JSONL = Path("checkpoints/analisis.jsonl")
LOG = Path("checkpoints/analisis.log")

log = logging.getLogger("analiza")
log.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
fh = logging.FileHandler(LOG, encoding="utf-8")
fh.setFormatter(fmt)
ch = logging.StreamHandler()
ch.setFormatter(fmt)
log.addHandler(fh)
log.addHandler(ch)


def cargar_preguntas() -> dict:
    cfg = json.loads(PREGUNTAS.read_text(encoding="utf-8"))
    perfil = cfg.get("perfil", "")
    preguntas = cfg["preguntas"]
    for q in preguntas.values():
        if "perfil" in q.get("instructions", ""):
            q["instructions"] = q["instructions"].format(perfil=perfil)
    return preguntas


def construir_state(fila: dict) -> dict:
    """Texto que ve el modelo: solo campos con información real."""
    campos = ("titulo", "empresa", "ocupacion", "ubicacion", "jornada", "salario",
              "nivel_academico", "experiencia", "tipo_contratacion",
              "fecha_publicacion", "fecha_vencimiento", "descripcion", "requisitos",
              "habilidades")
    state = {}
    for c in campos:
        v = (fila.get(c) or "").strip()
        if v:
            state[c] = v
    return state


def cargar_hechos() -> dict:
    if not JSONL.exists():
        return {}
    out = {}
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            out[obj["id"]] = obj
    return out


def extraer(res: dict, preguntas: dict) -> dict:
    """Convierte la respuesta de Laya en columnas planas."""
    fila = {}
    for qname in preguntas:
        a = res.get("answers", {}).get(qname, {})
        t = a.get("type")
        if t == "choice":
            fila[qname] = a.get("choice", "")
            fila[f"{qname}_confianza"] = a.get("answer_confidence", "")
        elif t == "score":
            escala = a.get("legend", {})
            s = a.get("score")
            idx = str(max(0, min(len(escala) - 1, int(round(s)))) if s is not None else "")
            fila[qname] = escala.get(idx, "")
            fila[f"{qname}_valor"] = round(s, 3) if s is not None else ""
            fila[f"{qname}_confianza"] = a.get("answer_confidence", "")
        else:
            fila[qname] = a.get(t, "")
            fila[f"{qname}_confianza"] = a.get("answer_confidence", "")
    return fila


def main() -> int:
    ap = argparse.ArgumentParser(description="Analiza el CSV con Laya")
    ap.add_argument("--max", type=int, default=0, help="limita filas en esta pasada")
    ap.add_argument("--limpiar", action="store_true", help="borra analisis previo")
    ap.add_argument("--lote", type=int, default=25, help="filas por escritura de CSV")
    args = ap.parse_args()

    if args.limpiar and JSONL.exists():
        JSONL.unlink()
        log.info("analisis previo borrado")

    preguntas = cargar_preguntas()
    hechos = cargar_hechos()
    log.info("preguntas: %s | ya analizadas: %d", ", ".join(preguntas), len(hechos))

    filas = list(csv.DictReader(ENTRADA.open(encoding="utf-8-sig")))
    log.info("csv de entrada: %d filas", len(filas))

    log.info("cargando Laya (Router)...")
    t0 = time.time()
    router = Router()
    log.info("Router listo en %.1fs", time.time() - t0)

    procesadas = 0
    for i, fila in enumerate(filas, 1):
        if fila["id"] in hechos:
            continue
        if args.max and procesadas >= args.max:
            log.info("límite --max alcanzado")
            break
        state = construir_state(fila)
        try:
            res = router.predict(state, preguntas, model="multilingual", max_len=8192)
        except Exception as e:  # noqa: BLE001
            log.error("fallo en %s: %s; reintento", fila["id"], e)
            time.sleep(3)
            try:
                res = router.predict(state, preguntas, model="multilingual", max_len=8192)
            except Exception as e2:  # noqa: BLE001
                log.error("segundo fallo en %s: %s; se salta", fila["id"], e2)
                continue
        reg = {"id": fila["id"], **extraer(res, preguntas)}
        with JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        hechos[fila["id"]] = reg
        procesadas += 1
        if procesadas % args.lote == 0:
            escribir_csv(filas, hechos, preguntas)
            log.info("analizadas %d (fila %d/%d, %.2fs/media)",
                     procesadas, i, len(filas), (time.time() - t0) / procesadas)

    n = escribir_csv(filas, hechos, preguntas)
    log.info("CSV FINAL: %s (%d filas analizadas)", SALIDA, n)
    return 0


def escribir_csv(filas: list[dict], hechos: dict, preguntas: dict) -> int:
    cols_orig = list(filas[0].keys())
    cols_anx = []
    for q, spec in preguntas.items():
        cols_anx.append(q)
        cols_anx.append(f"{q}_confianza")
        if spec.get("type") == "score":
            cols_anx.append(f"{q}_valor")
    fieldnames = cols_orig + cols_anx
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        n = 0
        for fila in filas:
            reg = dict(fila)
            reg.update(hechos.get(fila["id"], {}))
            w.writerow(reg)
            if fila["id"] in hechos:
                n += 1
    return n


if __name__ == "__main__":
    sys.exit(main())
