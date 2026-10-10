"""Exporta reporte simple diario de puestos NUEVOS (--nuevos por defecto).

Lee salida/puestos_enriquecidos.csv y salida/historial_ids.txt.
Escribe salida/puestos_simple_YYYY-MM-DD.xlsx con 18 columnas esenciales.
Actualiza historial_ids.txt con todos los IDs actuales tras exportar.

Uso:
    python export_simple.py                    # exporta nuevos
    python export_simple.py --output RUTA      # ruta personalizada
"""
import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    raise SystemExit("Falta openpyxl: .venv\\Scripts\\python.exe -m pip install openpyxl")

SRC = Path("salida/puestos_enriquecidos.csv")
HISTORIAL = Path("salida/historial_ids.txt")
SALIDA_DIR = Path("salida")

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}
RE_FECHA = re.compile(
    r"^\s*[a-záéíóúñ]+,?\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+del?\s+(\d{4})\s*$", re.I)

COLUMNAS_SALIDA = [
    "id", "titulo", "empresa", "descripcion", "requisitos",
    "provincia", "canton", "distrito",
    "fecha_publicacion", "fecha_vencimiento",
    "jornada", "salario", "plazas",
    "correo", "url",
    "modalidad_trabajo", "habilidades", "tipo_contratacion",
]

ANCHOS = {
    "id": 10, "titulo": 40, "empresa": 35, "descripcion": 60, "requisitos": 60,
    "provincia": 18, "canton": 20, "distrito": 22,
    "fecha_publicacion": 14, "fecha_vencimiento": 14,
    "jornada": 35, "salario": 22, "plazas": 8,
    "correo": 35, "url": 45,
    "modalidad_trabajo": 16, "habilidades": 45, "tipo_contratacion": 22,
}


def parsear_fecha(txt):
    """Convierte 'miércoles, 30 de septiembre del 2026' -> date(2026,9,30) o None."""
    m = RE_FECHA.match(txt or "")
    if not m:
        return None
    dia, mes, anio = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    if mes not in MESES:
        return None
    try:
        return dt.date(anio, MESES[mes], dia)
    except ValueError:
        return None


def leer_historial():
    """Devuelve set de IDs leídos del historial; set() si no existe."""
    try:
        with open(HISTORIAL, encoding="utf-8") as fh:
            return {int(line.strip()) for line in fh if line.strip().isdigit()}
    except FileNotFoundError:
        return set()


def guardar_historial(ids):
    """Escribe IDs ordenados al historial (uno por línea)."""
    with open(HISTORIAL, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(f"{i}\n" for i in sorted(ids)))


def a_int(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def main():
    ap = argparse.ArgumentParser(description="Exporta reporte simple de puestos nuevos a XLSX")
    ap.add_argument("--output", default=None, help="Ruta XLSX de salida (default: salida/puestos_simple_<hoy>.xlsx)")
    args = ap.parse_args()

    # Determinar archivo de salida
    if args.output:
        dst = Path(args.output)
    else:
        dst = SALIDA_DIR / f"puestos_simple_{dt.date.today().isoformat()}.xlsx"
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Leer CSV enriquecido
    if not SRC.exists():
        raise SystemExit(f"No existe {SRC}. Ejecute reglas.py primero.")
    with open(SRC, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"{SRC} está vacío.")

    # Leer historial y filtrar nuevos
    hist = leer_historial()
    nuevos = []
    ids_actuales = set()
    for r in rows:
        i = a_int(r.get("id", ""))
        if i is not None:
            ids_actuales.add(i)
        if hist and i is not None and i in hist:
            continue
        nuevos.append(r)

    if not nuevos:
        print("  sin puestos nuevos: no se genera archivo")
        return

    print(f"  historial: {len(hist)} ids")
    print(f"  nuevos: {len(nuevos)} de {len(ids_actuales)} puestos actuales")

    # Construir filas de salida
    datos = []
    for r in nuevos:
        fila = []
        for c in COLUMNAS_SALIDA:
            val = r.get(c, "")
            if c == "fecha_vencimiento":
                val = parsear_fecha(val)
            fila.append(val)
        datos.append(fila)

    # Escribir Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "puestos"
    ws.append(COLUMNAS_SALIDA)

    for fila in datos:
        ws.append(fila)

    # Formato encabezado
    hdr_fill = PatternFill("solid", fgColor="D9E1F2")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = hdr_fill
        cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNAS_SALIDA))}{len(datos) + 1}"

    # Anchos de columna
    for idx, nombre in enumerate(COLUMNAS_SALIDA, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ANCHOS.get(nombre, 20)

    # Formato fecha en fecha_vencimiento
    idx_fv = COLUMNAS_SALIDA.index("fecha_vencimiento") + 1
    for fila in ws.iter_rows(min_row=2, min_col=idx_fv, max_col=idx_fv):
        cell = fila[0]
        if isinstance(cell.value, dt.date):
            cell.number_format = "yyyy-mm-dd"

    try:
        wb.save(dst)
    except PermissionError:
        raise SystemExit(
            f"ERROR: no se pudo escribir {dst}\n"
            "  Causa: el archivo está ABIERTO en Excel (bloqueado).\n"
            "  Cierre ese archivo en Excel y vuelva a ejecutar."
        )

    # Actualizar historial con TODOS los IDs actuales
    guardar_historial(hist | ids_actuales)
    print(f"  historial actualizado: {len(hist)} -> {len(hist | ids_actuales)} ids -> {HISTORIAL}")

    # Verificación rápida
    wb2 = __import__("openpyxl").load_workbook(dst)
    ws2 = wb2["puestos"]
    n_cols = ws2.max_column
    n_filas = ws2.max_row
    print(f"OK: {dst} | {n_filas - 1} filas x {n_cols} columnas")


if __name__ == "__main__":
    main()