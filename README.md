# ANE Scraper

Scraper para el portal de empleo de la ANE (https://www.ane.cr). Extrae listados de puestos, obtiene detalles completos y genera reportes en Excel.

## Requisitos

- Python 3.10+
- **Brave Browser** con depuración remota habilitada
- Cuenta ANE con sesión iniciada en Brave

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar Playwright browsers
.venv\Scripts\playwright install chromium
```

## Configuración de Brave

Ejecutar Brave con depuración remota (puerto 9222):

```powershell
# Windows PowerShell
./run_brave.ps1
```

Luego iniciar sesión en https://www.ane.cr en esa ventana de Brave.

## Flujo de trabajo diario

```bash
# 1. Scrapear listados y detalles (reanudable)
python scrape.py

# 2. Enriquecer datos (reglas regex: modalidad, licencia, jornada, salario, experiencia)
python reglas.py

# 3. Generar reporte SOLO de puestos NUEVOS (desde último reporte)
python export_simple.py
# → salida/puestos_simple_YYYY-MM-DD.xlsx

# Opcional: Reporte completo con filtros
python a_excel.py --vigentes --nuevos
# → salida/puestos_nuevos_YYYY-MM-DD.xlsx (solo vigentes)
```

## Archivos principales

| Archivo | Descripción |
|---------|-------------|
| `scrape.py` | Scraper principal (2 fases: listado + detalle). Reanudable vía checkpoints. |
| `reglas.py` | Enriquece CSV con columnas derivadas (modalidad, licencia, jornada, salario, experiencia). |
| `export_simple.py` | Genera XLSX limpio (18 cols) solo de puestos nuevos. Actualiza historial. |
| `a_excel.py` | Exporta a Excel con subdivisión de columnas, filtros (--vigentes, --nuevos). |
| `historial.py` | Módulo compartido para gestión de historial de IDs. |

## Estructura de datos

```
salida/
├── puestos.csv              # CSV crudo (scrape.py)
├── puestos_enriquecidos.csv # CSV con columnas derivadas (reglas.py)
├── historial_ids.txt        # IDs ya reportados (una línea por ID)
├── puestos_simple_YYYY-MM-DD.xlsx   # Reporte diario limpio (export_simple.py)
├── puestos_nuevos_YYYY-MM-DD.xlsx   # Reporte con filtros (a_excel.py --nuevos)
└── puestos_vigentes.xlsx    # Solo vigentes (a_excel.py --vigentes)

checkpoints/
├── state.json               # Estado del scraper (fase, página, total)
├── listado.jsonl            # Tarjetas de listado (fase 1)
├── registros.jsonl          # Registros completos (fase 2)
└── scrape.log               # Log del scraper
```

## Columnas en reporte simple (`export_simple.py`)

| Categoría | Columnas |
|-----------|----------|
| Básicas | `id`, `titulo`, `empresa`, `descripcion`, `requisitos` |
| Ubicación | `provincia`, `canton`, `distrito` |
| Fechas | `fecha_publicacion`, `fecha_vencimiento` (fecha real Excel) |
| Detalles | `jornada`, `salario`, `plazas`, `tipo_contratacion` |
| Contacto | `correo`, `url` |
| Enriquecidas | `modalidad_trabajo`, `habilidades` |

## Funcionamiento del historial

- `historial_ids.txt` almacena **todos los IDs ya exportados**
- `export_simple.py --nuevos` (por defecto) compara contra historial
- Tras exportar, historial se actualiza con **todos los IDs actuales**
- Ejecuciones posteriores mismo día → "sin puestos nuevos"

## Comandos útiles

```bash
# Resetear historial (próxima exportación = todos como nuevos)
echo. > salida/historial_ids.txt

# Scraper solo listado (rápido)
python scrape.py --solo-listado

# Limitar detalles en esta pasada
python scrape.py --max-detalles 100

# Ver estado actual
cat checkpoints/state.json

# Ver log
tail -f checkpoints/scrape.log
```

## Notas

- El scraper usa la **sesión de Brave** (CDP en puerto 9222). No maneja login automático.
- Si la sesión expira: error "detalle sin contenedor" → iniciar sesión en Brave y reejecutar.
- `scrape.py` es **reanudable**: si se interrumpe, vuelve a ejecutar y continúa.
- `fecha_vencimiento` se parsea a fecha real de Excel (formato YYYY-MM-DD).