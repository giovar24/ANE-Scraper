"""Columnas deterministas por regex sobre salida/puestos.csv -> salida/puestos_enriquecidos.csv."""
import csv
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "salida/puestos.csv"
DST = "salida/puestos_enriquecidos.csv"

RE_TELETRABAJO = re.compile(
    r"teletrabajo|trabajo\s+remoto|modalidad\s+remota|desde\s+casa|home\s*office", re.I)
RE_HIBRIDO = re.compile(r"h[íi]brid", re.I)
RE_LIC_CAT = re.compile(r"licen[cs]i[ae](?:s)?\b\s*(?:clase|categor[íi]a)?\s*([bdc]\s?[-–]?\s?\d)", re.I)
RE_LIC_ABREV = re.compile(r"\blic\.?\s*([bdc]\s?[-–]?\s?\d)", re.I)
RE_LIC_BARE = re.compile(r"\b([bdc]\s?[-–]?\s?\d)\b", re.I)
RE_LIC_CUALQUIERA = re.compile(r"licen[cs]i[ae](?:s)?\b|conducir", re.I)
RE_LIC_NEGADA = re.compile(r"(?:sin|no\s+(?:se\s+)?requiere(?:\s+de)?)\s+licen[cs]i[ae](?:s)?\b", re.I)

EXPERIENCIA = [
    (re.compile(r"^sin experiencia", re.I), "sin_experiencia", 0.0),
    (re.compile(r"^pr[áa]ctica", re.I), "practica_supervisada", 0.0),
    (re.compile(r"^de 1 a menos de 12 meses", re.I), "1_12_meses", 1.0),
    (re.compile(r"^de 1 a menos de 2 a[ñn]os", re.I), "1_2_anios", 1.0),
    (re.compile(r"^de 2 a menos de 5 a[ñn]os", re.I), "2_5_anios", 2.0),
    (re.compile(r"^de 5 a menos de 10 a[ñn]os", re.I), "5_10_anios", 5.0),
    (re.compile(r"^10 a[ñn]os y m[áa]s", re.I), "10_mas_anios", 10.0),
]

RE_JORNADA = re.compile(r"^(?P<tipo>[^(]+?)\s*\((?P<horario>[^)]+)\)\s*$")

TIPOS_JORNADA = [
    (re.compile(r"^tiempo completo$", re.I), "tiempo_completo"),
    (re.compile(r"^por horas$", re.I), "por_horas"),
    (re.compile(r"^(?:½|1\s?/\s?2)\s?tiempo$", re.I), "media_tiempo"),
    (re.compile(r"^¾\s?tiempo$", re.I), "tres_cuartos_tiempo"),
    (re.compile(r"^¼\s?tiempo$", re.I), "un_cuarto_tiempo"),
    (re.compile(r"^otro$", re.I), "otro"),
    (re.compile(r"^cualquiera$", re.I), "cualquiera"),
]


def col_texto(f, *campos):
    return " ".join(f.get(c, "") or "" for c in campos)


def detectar_licencia(txt):
    if RE_LIC_NEGADA.search(txt) and not RE_LIC_ABREV.search(txt):
        return "no", ""
    cats = [re.sub(r"[\s\-–]", "", c).upper() for c in RE_LIC_CAT.findall(txt)]
    cats += [re.sub(r"[\s\-–]", "", c).upper() for c in RE_LIC_ABREV.findall(txt)]
    if cats:
        return "si", ";".join(sorted(set(cats)))
    if RE_LIC_BARE.search(txt) and RE_LIC_CUALQUIERA.search(txt):
        return "si", ";".join(sorted(set(re.sub(r"[\s\-–]", "", c).upper()
                                         for c in RE_LIC_BARE.findall(txt))))
    if RE_LIC_CUALQUIERA.search(txt):
        return "si", "menciona"
    return "no", ""


def detectar_jornada(valor):
    m = RE_JORNADA.match((valor or "").strip())
    if not m:
        return "desconocida", "desconocido"
    tipo = m.group("tipo").strip()
    for rx, canonic in TIPOS_JORNADA:
        if rx.match(tipo):
            return canonic, m.group("horario").strip().lower()
    return "desconocida", m.group("horario").strip().lower()


def detectar_experiencia(valor):
    v = (valor or "").strip()
    requerida = bool(re.search(r"\(Requerido\)\s*$", v, re.I))
    base = re.sub(r"\s*\(Requerido\)\s*$", "", v, flags=re.I).strip()
    for rx, cat, min_anios in EXPERIENCIA:
        if rx.match(base):
            return cat, ("si" if requerida else "no"), min_anios
    return "desconocida", ("si" if requerida else "no"), ""


def detectar_salario(salario):
    m = re.match(r"^₡\s*([\d.]+)\s*-\s*₡\s*([\d.]+)$", (salario or "").strip())
    if not m:
        return "", "", "no"
    lo = int(m.group(1).replace(".", ""))
    hi = int(m.group(2).replace(".", ""))
    publicado = "si" if lo >= 1000 else "no"
    return lo, hi, publicado


def main():
    with open(SRC, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("puestos.csv vacio")

    extras = ["modalidad_trabajo", "pide_licencia", "licencia_categorias", "jornada_tipo",
              "jornada_horario", "experiencia_categoria", "experiencia_requerida",
              "experiencia_min_anios", "salario_min_crc", "salario_max_crc",
              "salario_publicado"]
    campos = list(rows[0].keys()) + extras
    resumen = {"modalidad_trabajo": {}, "pide_licencia": 0, "salario_publicado": 0}

    for f in rows:
        txt_todos = col_texto(f, "titulo", "jornada", "descripcion", "requisitos",
                              "habilidades", "tipo_contratacion")
        if RE_TELETRABAJO.search(txt_todos):
            f["modalidad_trabajo"] = "teletrabajo"
        elif RE_HIBRIDO.search(txt_todos):
            f["modalidad_trabajo"] = "hibrido"
        else:
            f["modalidad_trabajo"] = "presencial"

        txt_req = col_texto(f, "titulo", "requisitos", "habilidades", "jornada")
        lic, cats = detectar_licencia(txt_req)
        f["pide_licencia"], f["licencia_categorias"] = lic, cats

        f["jornada_tipo"], f["jornada_horario"] = detectar_jornada(f.get("jornada", ""))

        cat, req, min_anios = detectar_experiencia(f.get("experiencia", ""))
        f["experiencia_categoria"] = cat
        f["experiencia_requerida"] = req
        f["experiencia_min_anios"] = min_anios

        lo, hi, pub = detectar_salario(f.get("salario", ""))
        f["salario_min_crc"], f["salario_max_crc"], f["salario_publicado"] = lo, hi, pub

        resumen["modalidad_trabajo"][f["modalidad_trabajo"]] = \
            resumen["modalidad_trabajo"].get(f["modalidad_trabajo"], 0) + 1
        if f["pide_licencia"] == "si":
            resumen["pide_licencia"] += 1
        if f["salario_publicado"] == "si":
            resumen["salario_publicado"] += 1

    with open(DST, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(rows)

    print(f"OK: {len(rows)} filas -> {DST} (+{len(extras)} columnas)")
    for k, v in resumen.items():
        print(f"  {k}: {v}")
    import collections
    for c in ("jornada_tipo", "experiencia_categoria", "experiencia_requerida"):
        print(f"  {c}: {dict(collections.Counter(r[c] for r in rows).most_common())}")


if __name__ == "__main__":
    main()
