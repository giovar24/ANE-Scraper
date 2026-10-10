# ANE Scraper — Plan y Log de Progreso

> **Cómo retomar tras perder contexto:** leer este archivo completo, revisar la sección
> "Estado" y ejecutar el paso marcado como SIGUIENTE. **En uso normal basta
> `run.bat`** (hace todo el flujo). El detalle técnico de cada fase está al final.
> Los datos de reanudación automática del scraper están en `checkpoints/state.json`.

## Estado

| Paso | Descripción | Estado | Fecha |
|------|-------------|--------|-------|
| F0 | venv + dependencias | HECHO | 2026-09-25 |
| F1 | run_brave.ps1 (Brave puerto 9222) | HECHO | 2026-09-25 |
| F2 | Exploración CDP: sesión, URL detalle, selectores | HECHO | 2026-09-25 |
| F3 | Pasada 1: listado `/Puesto?Pagina=N` | HECHO (1.984 únicos, 248 págs) | 2026-09-25 |
| F4 | Pasada 2: detalles con sesión | HECHO (1.984/1.984) | 2026-09-25 |
| F5 | Verificación CSV | HECHO | 2026-09-25 |
| F6 | análisis de puestos (reglas) | COMPLETADA (reglas) | 2026-09-25 |
| F7 | Export a Excel (`a_excel.py`) | HECHO (1984 × 33) | 2026-09-25 |
| F8 | `run.bat` — menú de opciones | HECHO (5 opciones probadas) | 2026-09-25 |
| F9 | Filtro de vacantes vigentes (2 archivos Excel) | HECHO (probado end-to-end) | 2026-09-26 |
| F10 | Filtro de puestos NUEVOS vs historial de ids | HECHO (probado end-to-end) | 2026-09-29 |

## F6 entregado — reglas deterministas (`reglas.py`)

`python reglas.py` → `salida/puestos_enriquecidos.csv` (1984 filas × 30 cols =
las 19 de puestos.csv + 11 derivadas):

- `modalidad_trabajo`: presencial=1981, hibrido=3, teletrabajo=0 (dato real, no bug)
- `pide_licencia` + `licencia_categorias` (B1=63, B2=26, B3=13, D3=10, menciona=63…) → 184 sí
- `jornada_tipo` (tiempo_completo=1660, otro=186, cualquiera=79, media=30, por_horas=21, ¾=4, ¼=4)
  y `jornada_horario` (diurna/rotativo/mixta/nocturna/cualquiera)
- `experiencia_categoria` + `experiencia_requerida` (si=678) + `experiencia_min_anios`
- `salario_min_crc`, `salario_max_crc`, `salario_publicado` (si=1111; ₡1-₡11 = placeholder
  → publicado=no; 490 vacíos = "Confidencial")

Bugs corregidos durante validación: falta `re.I` en jornada y en `[bdc]\d`
("B1" mayúscula no detectaba), `\b` final para excluir "licenciatura/licenciado"
(título académico ≠ licencia de conducir, 27 falsos), símbolos ½¾¼ y "B-1" con guión.

## F7 — Export a Excel (`a_excel.py`) — 2026-09-25

Problema reportado: al cargar el CSV en Excel se "mezclaban" las columnas.
Diagnóstico: los CSV están bien formados (1985 filas × ancho fijo, comillas OK);
la causa era `fecha_vencimiento` = "miércoles, 30 de septiembre del 2026" **con
coma** + campos compuestos. Solución: `python a_excel.py` → `salida/puestos.xlsx`
(1984 × 33, 865 KB), que Excel abre sin interpretación de delimitadores:

- `ubicacion` → `provincia`, `canton`, `distrito` (partición por " / ")
- `fecha_vencimiento` → fecha real de Excel (1984/1984 parseadas, 0 fallos)
- `nivel_academico` → `nivel_academico` + `nivel_requerido` (si/no)
- números reales: id, plazas, salario_min/max_crc, experiencia_min_anios
- formato: cabecera con filtro, panel congelado, columnas con ancho, fechas yyyy-mm-dd
- incluye las 11 columnas de reglas (F6)

## F8 — `run.bat` (orquestador, 1 comando) — 2026-09-25

Doble clic en `run.bat` ejecuta todo el flujo en orden:

1. Solo si falta `.venv`: crea entorno e instala `requirements.txt`
2. Comprueba puerto 9222; si no responde lanza `run_brave.ps1` y espera hasta 30 s
3. `check_session.py` (ahora con exit code 0/1) — si no hay sesión ANE: aviso
   claro ("inicie sesión en ane.cr y vuelva a ejecutar") y sale con código 1
4. `scrape.py` (retomable) → 5. `reglas.py` → 6. `a_excel.py`
7. Abre `salida/puestos.xlsx`

Probado: 2 corridas — puerto libre → relanza Brave → espera → detecta sesión
caducada → mensaje + exit 1. ASCII+CRLF (compatibilidad cmd), `chcp 65001` para
salida UTF-8 de Python. Acompañantes: `check_session.py` ahora `sys.exit(0/1)`;
`run_brave.ps1` con BOM UTF-8 (corrige "depuraciÃ³n" en PowerShell 5.1).

### Menú de `run.bat` (F8b — versión con opciones)

Al ejecutarlo muestra un menú con explicación de cada opción:

| Opción | Qué hace | Tiempo real |
|---|---|---|
| **1** Ejecutar (normal) | Reutiliza lo scrapeado; si todo completo solo regenera columnas+Excel | ~15 s |
| **2** Buscar puestos nuevos | `reset_state.py` + pipeline: re-escanea las páginas, **agrega** IDs nuevos, **conserva** histórico (dados de baja se quedan) | **~5 min** (medido) |
| **3** Frescos desde cero | `scrape.py --limpiar`: borra todo, snapshot exacto del portal de hoy | ~30-40 min |
| **4** Solo regenerar Excel | `reglas.py` + `a_excel.py`, sin Brave ni sesión | ~5 s |
| **5** Comprobar sesión | `check_session.py` (LOGIN ACTIVO) | ~5 s |
| **0** Salir | — | — |

Errores/sesión caducada → mensaje accionable y **vuelve al menú** (no sale).

Pruebas reales (2026-09-25): opciones inválida, 5, 1, 4 y **2 completas** —
la 2 encontró **+57 puestos nuevos** (1.984 → **2.041**, total del sitio2006+),
conservó los viejos y regeneró CSV/XLSX. Hallazgo: `a_excel.py` ahora atrapa
`PermissionError` ("el archivo está ABIERTO en Excel, ciérralo") en vez de
traceback — detectado porque la prueba anterior dejó el xlsx abierto.

### Filtro de vacantes vigentes (F9)

Para buscar trabajo sobran los registros vencidos (y el histórico crece).
`a_excel.py` gana dos flags:

- `--vigentes`: conserva solo filas con `fecha_vencimiento >= hoy` e imprime
  incluidos/excluidos; sin fecha parseable se conserva (0 casos en los datos).
- `--salida RUTA`: ruta del xlsx (default `salida/puestos.xlsx`).

**Cada operación del menú genera DOS archivos** (elegir según propósito):

| Archivo | Contenido | Uso |
|---|---|---|
| `salida/puestos.xlsx` | TODOS los registros | histórico / estadística |
| `salida/puestos_vigentes.xlsx` | SOLO vigentes (fecha de vencimiento ≥ hoy) | buscar trabajo sin ruido |

Prueba 26/9 (opción 4 end-to-end): 1.850 → **1.831 vigentes** (19 vencidos
excluidos), verificación independiente 1.831/1.831 con fecha ≥ hoy, 0
residuales, EXIT=0.

**Bugs corregidos durante la prueba:**
1. `echo` con `>=` en run.bat → cmd lo interpretaba como redirección (borraba
   la línea y creaba archivos basura). Reescrito sin símbolos.
2. `set /p` con stdin de pipe deja `op = "4\r"` → `if "%op%"=="4"` traba cmd
   ("La sintaxis del comando no es correcta"). Fix:
   `if defined op set "op=%op:~0,1%"` — sin `if defined`, el substring con
   variable vacía produce literal `~0,1` → loop infinito de menú (verificado).
3. `pause` con stdin de pipe se cuelga y `cls`/`chcp` rompen la lectura desde
   archivo: solo afecta a tests automatizados; en consola interactiva (doble
   clic, uso real) no aplica.

## Filtro de puestos NUEVOS vs historial (F10)

Cada puesto tiene un número de referencia (`id`) en la BD de ANE. Se quiere saber
**qué puestos son nuevos desde la última corrida**, sin re-leer 2.000 filas a mano.

- **`salida/historial_ids.txt`** (nuevo): solo los ids registrados, uno por línea,
  orden ascendente y sin duplicados → la última línea = el último puesto del historial.
- **`a_excel.py --nuevos`**: exporta SOLO los puestos `id no en historial` **e**
  `id > último del historial`. Destino por defecto con fecha:
  `salida/puestos_nuevos_YYYY-MM-DD.xlsx` (misma fecha = se sobrescribe).
  Tras guardar el xlsx, **actualiza el historial automáticamente** con la unión de
  los ids previos + **todos** los ids actuales del CSV (un id "no elegible" por ser
  ≤ máximo también queda registrado).
- **Primera corrida** (sin archivo de historial): se exportan todos y se siembra
  el historial. Corridas siguientes: solo los nuevos de verdad.
- `run.bat`: pipeline (paso 4/4) y opción 4 ejecutan `a_excel.py --nuevos`;
  el menú y `:listo` mencionan el **tercer** archivo.
- Flags composables: `--nuevos --vigentes` = solo nuevos que además están vigentes.

Prueba aislada (2026-09-29, carpeta temporal con CSV de prueba, 3 escenarios):
(1) sin historial → 5/5 exportados, historial sembrado ordenado; (2) con historial
en 112 → de 8 filas salen solo 115 y 120 (el 95, no registrado pero ≤112, queda
fuera por la regla del consecutivo) y el historial pasa a 8 ids; (3) repetir →
0 nuevos, EXIT=0. Además: modo sin flags y `--vigentes --salida` intactos.

**Precaución:** no correr `--nuevos` con el scrape a medias — sembraría el
historial con ids parciales (el detalle baja de id) y los pendientes nunca
aparecerían como nuevos. Ejecutar cuando el scrape esté completo.

## Hallazgos Laya (calibración) — F6b pendiente si se quiere



`laya 0.3.20` instalado (torch CPU). `preguntas.json` define las preguntas tipadas
(decision/teletrabajo/exigencia). **Validación contra 40 filas reales del CSV con
ground truth por regex** (`valida.py`):

| Pregunta | Precisión Laya (zero-shot) |
|---|---|
| teletrabajo | 20% (estado largo) / 15% (estado corto) |
| licencia | 5-42% |
| jornada tiempo completo | 95% (pero es clase mayoritaria ~90%, no acredita) |
| encaja con mi perfil (calibra.py) | falla 2/2 casos de prueba |
| checkpoint `typed-decisions` | 0/40 y 2/40 (fine-tune en inglés, no sirve aquí) |

**Diagnóstico:** el modelo responde por asociación ("chofer → licencia",
"sistemas → teletrabajo") con confianza 0.7-0.9 en vez de leer el texto. Coincide
con los "Honest Limits" de la ficha: *base checkpoints near chance zero-shot
(0.362); la precisión llega con fine-tuning (0.766)*. Scripts: `probe_laya.py`,
`calibra.py`, `calibra2.py`, `calibra3.py`, `valida.py`, `valida_corto.py`.

**Opciones evaluadas (decisión 2026-09-25):** el usuario eligió (a) columnas
deterministas por regex — ENTREGADO arriba — dejando `analiza.py` + `preguntas.json`
listos para (c) fine-tune con ejemplos propios (notebook Kaggle, GPU) cuando se
quiera precisión real (~0.76 según ficha del modelo). Opción (b) ejecutar Laya
completo descartada por acertar ~50%. Falso positivo corregido en la validación:
mi GT no reconocía "Lic B1".

**ESTADO ACTUAL: PROCESO COMPLETADO + AUTOMATIZADO.** `run.bat` abre un **menú**
con las opciones (ver F8b): [1] normal, [2] buscar nuevos (~5 min), [3] desde
cero, [4] solo Excel, [5] sesión. Cada operación genera **DOS Excel** (F9):
`puestos.xlsx` (todos) + `puestos_vigentes.xlsx` (vigentes, abrir este para
buscar trabajo). Última corrida (26/9 17:00, op.1, sesión restaurada): **1.983
/ 1.983 detalles** → `puestos.xlsx` **1.983 × 33** y `puestos_vigentes.xlsx`
**1.864 × 33** (119 vencidos fuera, 0 sin fecha). La sesión ANE caduca ~30 min;
el menú lo detecta y avisa (iniciar sesión en Brave y reintentar).

## Log

- `[F0] 2026-09-25` OK — venv `.venv`, instalados playwright, beautifulsoup4, lxml.
- `[F1] 2026-09-25` OK — `run_brave.ps1` creado; Brave responde en `http://127.0.0.1:9222`.
- `[F2] 2026-09-25` OK — sesión activa (`__aneLoginToken`). URL detalle:
  `/Puesto/Detalles?Puesto=<id>`. Selectores extraídos (ver checkpoints/html/).
- `[F3] 2026-09-25` OK — 248 páginas, **1.984 puestos únicos** en
  `checkpoints/listado.jsonl`. Paginación real = **8 por página** (no 10).
  Bugs corregidos durante la fase: tope de páginas mal calculado, corte por
  "sin tarjetas nuevos" demasiado agresivo, transición listado→detalle, y
  marcado de "completado" prematuro al usar --max-detalles.
- `[F4] 2026-09-25` EN CURSO — detalles con `context.request` (sin renderizar).
  CSV se reescribe cada 25 detalles en `salida/puestos.csv`.
- `[F4a] 2026-09-25 14:17` CORTE — sesión caducada en el puesto 117489 tras
  **935/1.984 filas**. Causa: timeout de sesión del servidor (cookie
  `__aneLoginToken` desaparece sola). **No hace falta rehacer nada**: el CSV y
  `registros.jsonl` conservan lo hecho y el scraper retoma por diferencia.
  Lección: si vuelve a pasar, solo reloguear en ANE y relanzar `scrape.py`.
- `[F4b] 2026-09-25` sesión refrescada por el usuario -> reanudación (1.037
  detalles restantes procesados sin más cortes).
- `[F4c] 2026-09-25 14:41` OK — **1.984/1.984 detalles**. Estado: completado.
- `[F5] 2026-09-25` OK — verificación: 1.984 filas, 19 columnas, 0 ids
  duplicados, 0 fechas mal formateadas, codificación utf-8-sig.
  Vacíos esperados (el sitio no publica esos datos): salario 490, correo 490
  (mismas 490 filas — puestos "Confidencial"/sin remuneración publicada),
  requisitos 969 (969 no traen bloque "Requisitos adicionales"), habilidades 232.
  77 descripciones <30 car son reales (p.ej. "RESGUARDAR Y VIGILAR").
- `[F1b] 2026-09-25` NOTE — la sesión NO se conserva al cerrar Brave (la web llama a
  `/Cuenta/LogoutOnClose` al cerrar). Regla: **no cerrar Brave durante todo el proceso**;
  `run_brave.ps1` solo lo relanza si el puerto 9222 no responde.
- `[F6] 2026-09-25` OK — `reglas.py`: 11 columnas derivadas →
  `salida/puestos_enriquecidos.csv` (1984 × 30). Laya descartado para extracción
  (~50% real, validado contra 40 filas con GT por regex); `analiza.py` queda listo
  para un futuro fine-tune. Ver sección "Hallazgos Laya".
- `[F7] 2026-09-25` OK — `a_excel.py` → `salida/puestos.xlsx` (1984 × 33, 865 KB).
  Causa del "mezclado" en Excel: `fecha_vencimiento` = "miércoles, 30 de
  septiembre del 2026" **con coma** + campos compuestos (`ubicacion` con 3 niveles,
  `nivel_academico` con "(Requerido)"). 1984/1984 fechas parseadas, 0 fallos.
- `[F8] 2026-09-25` OK — `run.bat` creado y probado (2 corridas): valida puerto →
  lanza Brave → espera → check de sesión (exit 1 si caducada, mensaje accionable).
  Compañeros: `check_session.py` con exit code, `run_brave.ps1` con BOM UTF-8.
- `[F8b] 2026-09-25` OK — `run.bat` con **menú de opciones** (1 normal, 2 nuevos,
  3 desde cero, 4 solo Excel, 5 sesión, 0 salir), cada una con su explicación.
  Pruebas:9/5/1/4/2 — opción2 real: **+57 puestos** (1.984→2.041 en ~5 min),
  histórico conservado. Fix: `a_excel.py` maneja PermissionError (xlsx abierto
  en Excel) con mensaje claro en vez de traceback.
- `[F9] 2026-09-26` OK — filtro de **VIGENTES** (`a_excel.py --vigentes
  [--salida]`); run.bat genera `puestos.xlsx` (todos) +
  `puestos_vigentes.xlsx` en cada operación. Prueba opción4 end-to-end:
  1.850 → 1.831 (19 vencidos fuera), 0 residuales, EXIT=0. Fixes: `>=` en
  echo (redirección accidental), `set /p`+`\r` con `if defined`, loop `~0,1`.
- `[F9b] 2026-09-26 17:00` OK — **corrida real del usuario** (sesión
  restaurada): retomó los 133 detalles pendientes del corte de las 12:15 →
  **CSV FINAL 1.983 filas** + reglas + doble Excel. Verificado:
  csv 1.983×19, enriquecido 1.983×30, `puestos.xlsx` 1.983×33,
  `puestos_vigentes.xlsx` **1.864×33** (119 vencidos fuera, 0 sin fecha,
  1.864+119=1.983 ✓), ids únicos 1.983 (185–118718), state `completado`.
  Raíz y `salida\` sin archivos basura; 0 procesos colgados.
- `[F10] 2026-09-29` OK — **filtro de puestos NUEVOS vs historial**
  (`a_excel.py --nuevos`): lee/actualiza `salida/historial_ids.txt` (solo ids,
  ascendente, únicos) y escribe `salida/puestos_nuevos_YYYY-MM-DD.xlsx` con los
  ids no registrados **e** > último del historial; el historial se actualiza solo
  al guardar. run.bat: paso 4/4 y op.4 lo ejecutan; menú habla de TRES archivos.
  Prueba aislada 3 escenarios (5/5 primera, 2/8 segunda con 95 excluido por ≤
  máximo, 0/8 tercera), modos sin flags e `--vigentes` intactos, EXIT=0.
  NOTA: pendiente la 1ª corrida real (el scrape de hoy se cortó 12:02 con sesión
  caducada, 1.375/1.999) — NO correr `--nuevos` hasta completar el scrape.

## Hallazgos técnicos (F2 parcial)

- Listado público, server-side: `GET https://www.ane.cr/Puesto?Pagina=N` (10/página).
- Filtros GET: `Cat` (1-30 áreas), `Prov` (1-7), `Cant`, `Jornada` (2-5), `Salario`,
  `EmpresaPublica` (1=no aplica, 2=sí, 3=no), `Empleos` (keyword vía
  `/Puesto/AutoCompleteEmpleos`).
- Campos por tarjeta (`.job-listing`): `h4.job-listing-company` (empresa),
  `h3.job-listing-title` (puesto), `h4.job-listing-description` (ocupación; 2º = Plazas),
  `small.job-listing-description` ("Publicado el <día>, <dd> de <mes> del <aaaa>"),
  `ul > li` con `icon-material-outline-add-location` (ubicaciones).
- Selectores detalle: PENDIENTE (requiere sesión).
- `logout`: `var redireccion = '/Cuenta/LogoutOnClose'`.

## Estructura

```
run.bat            # F8: ORQUETADOR — 1 comando ejecuta todo el flujo (doble clic)
run_brave.ps1      # relanza Brave con --remote-debugging-port=9222 (no mata si ya corre)
check_session.py   # LOGIN ACTIVO True/False, exit code 0/1 (lo usa run.bat)
scrape.py          # F3+F4: scraper con reanudación (checkpoints/state.json) -> salida/puestos.csv
reglas.py          # F6: 11 columnas derivadas -> salida/puestos_enriquecidos.csv
a_excel.py         # F7: subdivisión de columnas + formato -> salida/puestos.xlsx
                   #      F10: --nuevos -> salida/puestos_nuevos_<fecha>.xlsx
                   #      + historial en salida/historial_ids.txt
analiza.py         # F6b: análisis con Laya (OPCIONAL, ~50% sin fine-tune)
preguntas.json     # preguntas tipadas para Laya (fine-tune futuro)
explore.py         # F2: descubre URL de detalle y selectores -> checkpoints/exploracion.json
requirements.txt   # playwright, beautifulsoup4, lxml, laya, openpyxl
```

## CSV / XLSX de salida

- `salida/puestos.csv` (F5): 1.984 × 19 — `id, titulo, empresa, ocupacion,
  fecha_publicacion, ubicacion, jornada, salario, plazas, nivel_academico,
  experiencia, tipo_contratacion, fecha_vencimiento, descripcion, requisitos,
  habilidades, correo, url, fecha_scrapeo` — `utf-8-sig`.
- `salida/puestos_enriquecidos.csv` (F6): +11 columnas de reglas (30 total).
- `salida/puestos.xlsx` (F7/F8): 1.984 × 33 — subdividido y con tipos de datos
  reales. **Este es el archivo para Excel.**
- `salida/puestos_nuevos_YYYY-MM-DD.xlsx` (F10): SOLO puestos nuevos vs
  `salida/historial_ids.txt` (ids no registrados y mayores que el último).
- `salida/historial_ids.txt` (F10): un id por línea, ascendente y sin duplicados;
  lo actualiza `a_excel.py --nuevos` al guardar.
