"""Scraper ANE (https://www.ane.cr) -> salida/puestos.csv

Fase 1 (listado): recorre /Puesto?Pagina=N y guarda tarjetas en checkpoints/listado.jsonl
Fase 2 (detalle): por cada puesto, /Puesto/Detalles?Puesto=<id> con la sesión de Brave
                  y guarda el registro completo en checkpoints/registros.jsonl

Reanudable: el estado vive en checkpoints/state.json; si se corta, vuelve a ejecutar
este mismo script y continúa donde quedó.

Requiere Brave con depuración remota (run_brave.ps1) y sesión ANE iniciada.
"""
import argparse
import csv
import json
import logging
import math
import random
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.ane.cr"
CDP = "http://127.0.0.1:9222"
CHK = Path("checkpoints")
SALIDA = Path("salida/puestos.csv")
LISTADO_JSONL = CHK / "listado.jsonl"
REG_JSONL = CHK / "registros.jsonl"
STATE_JSON = CHK / "state.json"

COLUMNAS = [
    "id", "titulo", "empresa", "ocupacion", "fecha_publicacion", "ubicacion",
    "jornada", "salario", "plazas", "nivel_academico", "experiencia",
    "tipo_contratacion", "fecha_vencimiento", "descripcion", "requisitos",
    "habilidades", "correo", "url", "fecha_scrapeo",
]

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# ---------------------------------------------------------------- logging
log = logging.getLogger("ane")
log.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
fh = logging.FileHandler(CHK / "scrape.log", encoding="utf-8")
fh.setFormatter(fmt)
ch = logging.StreamHandler()
ch.setFormatter(fmt)
log.addHandler(fh)
log.addHandler(ch)


def limpiar(t: str | None) -> str:
    """Colapsa espacios y limpia saltos de línea de un texto."""
    if not t:
        return ""
    return " ".join(t.replace("\xa0", " ").split())


# ---------------------------------------------------------------- estado
def cargar_state() -> dict:
    if STATE_JSON.exists():
        txt = STATE_JSON.read_text(encoding="utf-8-sig")
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            log.warning("state.json corrupto; se reinicia el estado")
    return {"fase": "listado", "siguiente_pagina": 1, "total_puestos": None}


def guardar_state(st: dict) -> None:
    STATE_JSON.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- parseo listado
def parse_fecha_listado(txt: str) -> str:
    """'Publicado el viernes, 25 de septiembre del 2026' -> '2026-09-25'"""
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+del\s+(\d{4})", txt, re.I)
    if not m:
        return ""
    dia, mes, anio = int(m.group(1)), MESES.get(m.group(2).lower().rstrip("."), 0), int(m.group(3))
    if not mes:
        return ""
    try:
        return date(anio, mes, dia).isoformat()
    except ValueError:
        return ""


def parse_listado(html: str) -> tuple[list[dict], int | None]:
    """Devuelve (tarjetas, total_resultados|None)."""
    soup = BeautifulSoup(html, "lxml")
    h3 = soup.find("h3", string=re.compile(r"Resultados encontrados"))
    total = None
    if h3:
        m = re.search(r"(\d[\d.]*)", h3.get_text())
        if m:
            total = int(m.group(1).replace(".", ""))

    cards = []
    for job in soup.select("div.job-listing"):
        box = job.select_one("div.job-listing-description")
        if not box:
            continue
        h4s = box.select("h4.job-listing-description")
        empresa = job.select_one("h4.job-listing-company")
        titulo = job.select_one("h3.job-listing-title")
        small = job.select_one("small.job-listing-description")
        link = job.select_one("a[href*='/Puesto/Detalles']")
        href = link.get("href", "") if link else ""
        pid = ""
        m = re.search(r"Puesto=(\d+)", href)
        if m:
            pid = m.group(1)
        if not pid or not titulo:
            continue
        plazas = ""
        for h4 in h4s:
            t = limpiar(h4.get_text())
            if t.lower().startswith("plazas"):
                plazas = t.split(":", 1)[-1].strip()
        ubic = [limpiar(li.get_text()) for li in box.select("ul > li")]
        cards.append({
            "id": pid,
            "titulo": limpiar(titulo.get_text()),
            "empresa": limpiar(empresa.get_text()) if empresa else "",
            "ocupacion": limpiar(h4s[0].get_text()) if h4s else "",
            "fecha_publicacion": parse_fecha_listado(limpiar(small.get_text())) if small else "",
            "ubicacion": "; ".join(dict.fromkeys(x for x in ubic if x)),
            "plazas": plazas,
            "url": BASE + href.split("&")[0] if href else "",
        })
    return cards, total


# ---------------------------------------------------------------- parseo detalle
def campo(cont, label: str) -> str:
    """<p><strong>ETIQUETA</strong>: valor (a veces en <span>)</p>"""
    if cont is None:
        return ""
    for p in cont.find_all("p"):
        s = p.find("strong")
        if s and limpiar(s.get_text()).rstrip(":").strip().lower() == label.lower():
            txt = limpiar(p.get_text(" ", strip=True))
            return txt.split(":", 1)[1].strip() if ":" in txt else ""
    return ""


def lista_tras(cont, label: str) -> list[str]:
    """<strong>ETIQUETA</strong>: ... <ul class="list-3"><li>...</li></ul>"""
    if cont is None:
        return []
    for s in cont.find_all("strong"):
        if label.lower() in limpiar(s.get_text()).lower():
            ul = s.find_next("ul", class_="list-3")
            if ul:
                return [limpiar(li.get_text()) for li in ul.find_all("li") if limpiar(li.get_text())]
    return []


def parse_detalle(html: str, tarjeta: dict) -> dict | None:
    """Devuelve el registro completo o None si la página no es un detalle (p.ej. login)."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one("div.dashboard-content-inner")
    if root is None:
        return None
    cajas = root.select("div.row > div.col-xl-6")
    izq = der = None
    if len(cajas) >= 1:
        izq = cajas[0].select_one("div.dashboard-box > div.content.with-padding")
    if len(cajas) >= 2:
        der = cajas[1].select_one("div.dashboard-box > div.content.with-padding")

    h2 = root.select_one("div.content.with-padding h2.text-center")
    sm = root.select_one("div.content.with-padding p.text-center small")

    plazas = tarjeta.get("plazas", "")
    for st in (izq or root).find_all("strong"):
        if "plazas disponibles" in limpiar(st.get_text()).lower():
            m = re.search(r"(\d+)", limpiar(st.get_text()))
            if m:
                plazas = m.group(1)
            break

    funciones = campo(der, "Funciones principales del empleo")
    reqs = campo(der, "Requisitos adicionales para el empleo")
    habilidades = lista_tras(der, "Habilidades importantes")

    desc = funciones or campo(der, "Detalle del horario")
    return {
        "id": tarjeta["id"],
        "titulo": limpiar(h2.get_text()) if h2 else tarjeta["titulo"],
        "empresa": limpiar(sm.get_text()) if sm else tarjeta["empresa"],
        "ocupacion": campo(izq, "Ocupación") or tarjeta["ocupacion"],
        "fecha_publicacion": tarjeta["fecha_publicacion"],
        "ubicacion": "; ".join(lista_tras(izq, "Ubicaciones del empleo")) or tarjeta["ubicacion"],
        "jornada": campo(der, "Horario"),
        "salario": campo(der, "Salario"),
        "plazas": plazas,
        "nivel_academico": campo(izq, "Nivel académico"),
        "experiencia": campo(izq, "Experiencia laboral"),
        "tipo_contratacion": campo(der, "Tipo contratación"),
        "fecha_vencimiento": campo(der, "Fecha de vencimiento de la vacante"),
        "descripcion": desc,
        "requisitos": reqs,
        "habilidades": "; ".join(habilidades),
        "correo": campo(izq, "Correo"),
        "url": tarjeta["url"],
        "fecha_scrapeo": date.today().isoformat(),
    }


# ---------------------------------------------------------------- CSV
def escribir_csv() -> int:
    registros = leer_jsonl(REG_JSONL)
    por_id = {r["id"]: r for r in registros}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        for r in por_id.values():
            w.writerow(r)
    return len(por_id)


# ---------------------------------------------------------------- HTTP via sesión Brave
def obtener(ctx, url: str, intentos: int = 3, requiere_sesion: bool = False) -> str | None:
    for i in range(intentos):
        try:
            resp = ctx.request.get(url, timeout=30000, fail_on_status_code=False)
            if resp.status == 404:
                return None
            if resp.status >= 500:
                raise RuntimeError(f"HTTP {resp.status}")
            html = resp.text()
            if requiere_sesion and "dashboard-content-inner" not in html:
                raise RuntimeError("detalle sin contenedor (¿sesión caducada?)")
            return html
        except Exception as e:  # noqa: BLE001
            espera = (2, 5, 10)[min(i, 2)]
            log.warning("fallo %s (%s); reintento %d/%d en %ds", url, e, i + 1, intentos, espera)
            if i == intentos - 1:
                raise
            time.sleep(espera)
    return None


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="Scraper ANE -> CSV")
    ap.add_argument("--max-paginas", type=int, default=0, help="limita páginas de listado")
    ap.add_argument("--max-detalles", type=int, default=0, help="limita detalles en esta pasada")
    ap.add_argument("--pausa", type=float, default=0.8, help="pausa base entre peticiones (s)")
    ap.add_argument("--limpiar", action="store_true", help="borra checkpoints y empieza de cero")
    ap.add_argument("--solo-listado", action="store_true")
    args = ap.parse_args()

    if args.limpiar:
        for p in (LISTADO_JSONL, REG_JSONL, STATE_JSON):
            if p.exists():
                p.unlink()
        log.info("checkpoints borrados")

    st = cargar_state()
    log.info("estado: fase=%s pagina=%s total=%s", st["fase"], st.get("siguiente_pagina"), st.get("total_puestos"))

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP, timeout=15000)
        except Exception:
            log.error("Brave no responde en %s -> ejecuta run_brave.ps1", CDP)
            return 2
        ctx = browser.contexts[0]

        # ------------------------------------------------ FASE 1: listado
        if st["fase"] == "listado":
            ids_vistos = {t["id"] for t in leer_jsonl(LISTADO_JSONL)}
            pagina = st.get("siguiente_pagina", 1)
            pagina_inicio = pagina
            page_size = st.get("page_size")
            vacias = 0
            fin_alcanzado = False
            while True:
                if args.max_paginas and pagina >= pagina_inicio + args.max_paginas:
                    log.info("límite --max-paginas alcanzado")
                    break
                url = f"{BASE}/Puesto?Pagina={pagina}"
                html = obtener(ctx, url)
                cards, total = parse_listado(html)
                if st.get("total_puestos") is None and total:
                    st["total_puestos"] = total
                    guardar_state(st)
                    log.info("total de puestos: %s", total)
                if not cards:
                    vacias += 1
                    log.info("página %d vacía (%d seguidas)", pagina, vacias)
                    if vacias >= 2:
                        fin_alcanzado = True
                        break
                else:
                    vacias = 0
                    if page_size is None:
                        page_size = len(cards)
                        st["page_size"] = page_size
                        guardar_state(st)
                    nuevos = [c for c in cards if c["id"] not in ids_vistos]
                    for c in nuevos:
                        append_jsonl(LISTADO_JSONL, c)
                    ids_vistos.update(c["id"] for c in nuevos)
                    total_paginas = math.ceil((st.get("total_puestos") or 0) / page_size)
                    log.info("listado página %d/%d: +%d (únicos %d)",
                             pagina, total_paginas, len(nuevos), len(ids_vistos))
                    if total_paginas and pagina >= total_paginas:
                        log.info("última página estimada (%d) alcanzada", total_paginas)
                        st["siguiente_pagina"] = pagina + 1
                        guardar_state(st)
                        fin_alcanzado = True
                        break
                st["siguiente_pagina"] = pagina + 1
                guardar_state(st)
                pagina += 1
                time.sleep(args.pausa * random.uniform(0.5, 1.0))

            if fin_alcanzado and not args.solo_listado and not args.max_paginas:
                st["fase"] = "detalle"
                guardar_state(st)
                log.info("listado COMPLETO (%d puestos únicos) -> fase detalle", len(ids_vistos))
            else:
                log.info("listado pausado en página %d (retomar con el mismo comando)", st["siguiente_pagina"])

        # ------------------------------------------------ FASE 2: detalles
        pendientes: list[dict] = []
        if st["fase"] in ("detalle", "completado") and not args.solo_listado:
            tarjetas = {t["id"]: t for t in leer_jsonl(LISTADO_JSONL)}
            hechos = {r["id"] for r in leer_jsonl(REG_JSONL)}
            pendientes = [t for tid, t in tarjetas.items() if tid not in hechos]
            log.info("detalles: %d pendientes de %d", len(pendientes), len(tarjetas))
            if not pendientes:
                st["fase"] = "completado"
                guardar_state(st)

            procesados = 0
            for i, tarjeta in enumerate(pendientes, 1):
                if args.max_detalles and procesados >= args.max_detalles:
                    log.info("límite --max-detalles alcanzado")
                    break
                try:
                    html = obtener(ctx, tarjeta["url"], requiere_sesion=True)
                except RuntimeError as e:
                    log.error("SESIÓN PROBLEMÁTICA en %s: %s", tarjeta["url"], e)
                    log.error("Inicia sesión en ANE en Brave y vuelve a ejecutar (retoma solo)")
                    return 3
                reg = parse_detalle(html, tarjeta) if html else None
                if reg is None:
                    log.warning("detalle vacío/404 para %s (%s)", tarjeta["id"], tarjeta["titulo"])
                    reg = {**tarjeta, "jornada": "", "salario": "", "nivel_academico": "",
                           "experiencia": "", "tipo_contratacion": "", "fecha_vencimiento": "",
                           "descripcion": "", "requisitos": "", "habilidades": "", "correo": "",
                           "fecha_scrapeo": date.today().isoformat()}
                append_jsonl(REG_JSONL, reg)
                procesados += 1
                if procesados % 25 == 0:
                    n = escribir_csv()
                    log.info("detalle %d/%d -> csv con %d filas (último: %s)",
                             i, len(pendientes), n, reg["titulo"][:50])
                time.sleep(args.pausa * random.uniform(0.6, 1.4))

            restantes = len(pendientes) - procesados
            if restantes <= 0:
                st = cargar_state()
                st["fase"] = "completado"
                guardar_state(st)
                log.info("todos los detalles procesados")
            else:
                log.info("detalles pausados: quedan %d (retoma con el mismo comando)", restantes)

        browser.close()

    n = escribir_csv()
    log.info("CSV FINAL: %s (%d filas)", SALIDA, n)
    log.info("LOG: %s | estado: %s", CHK / "scrape.log", STATE_JSON)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
