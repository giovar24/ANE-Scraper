"""Módulo compartido para gestión de historial de IDs."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HISTORIAL = Path("salida/historial_ids.txt")


def leer_historial() -> set[int]:
    """Devuelve set de IDs leídos del historial; set() si no existe."""
    try:
        with open(HISTORIAL, encoding="utf-8") as fh:
            return {int(line.strip()) for line in fh if line.strip().isdigit()}
    except FileNotFoundError:
        return set()


def guardar_historial(ids: set[int]) -> set[int]:
    """Escribe IDs ordenados al historial (uno por línea). Devuelve el set guardado."""
    HISTORIAL.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORIAL, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(f"{i}\n" for i in sorted(ids)))
    return ids


def a_int(valor: str | None) -> int | None:
    """Convierte a int o None si falla."""
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def filtrar_nuevos(rows: list[dict], hist: set[int] | None = None) -> tuple[list[dict], set[int]]:
    """
    Filtra filas que NO están en el historial.
    Returns: (nuevos, ids_actuales)
    """
    if hist is None:
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

    return nuevos, ids_actuales


def actualizar_historial(hist: set[int], ids_actuales: set[int]) -> set[int]:
    """Actualiza historial con todos los IDs actuales. Returns nuevo historial."""
    nuevo = hist | ids_actuales
    guardar_historial(nuevo)
    return nuevo