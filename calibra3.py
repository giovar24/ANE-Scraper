"""Calibración 3: estado como texto plano + consigna explícita de leer el texto."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import laya  # noqa: E402

agent = laya.load("convaiinnovations/laya", subfolder="multilingual")

CASOS = {
    "dev_tele": (
        "Puesto: Desarrollador Backend Python\n"
        "Descripcion: Buscamos desarrollador Python con experiencia en APIs REST. "
        "Modalidad teletrabajo, jornada tiempo completo. Proyecto indefinido.\n"
        "Requisitos: 3 anos de experiencia con Python, ingles intermedio. Licencia B1."
    ),
    "mecanico": (
        "Puesto: Tecnico en Cabezotes\n"
        "Descripcion: Experiencia minima de 3 anos en rectificacion de asientos de valvulas. "
        "Disponibilidad inmediata. Trabajo presencial en taller, San Jose.\n"
        "Requisitos: Secundaria tecnica completa. Sin licencia de conducir."
    ),
    "chofer": (
        "Puesto: Chofer Repartidor\n"
        "Descripcion: Reparto de mercaderia en ruta. Jornada diurna, tiempo completo.\n"
        "Requisitos: Licencia categoria B2 y B3 al dia. 2 anos de experiencia previa."
    ),
}

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
        "instructions": "Lee el texto del puesto. ¿Pide licencia de conducir? "
                        "Responde solo segun el texto.",
        "criteria": {
            "A": "el texto pide licencia de conducir",
            "B": "el texto no pide licencia",
        },
    },
    "anios_experiencia": {
        "type": "choice",
        "instructions": "Lee el texto del puesto. ¿Cuantos anos de experiencia pide? "
                        "Responde solo segun el texto.",
        "criteria": {
            "ninguna": "no pide experiencia",
            "1a2": "pide 1 o 2 anos",
            "3a5": "pide 3 a 5 anos",
            "mas5": "pide mas de 5 anos",
        },
    },
    "jornada_tiempo_completo": {
        "type": "choice",
        "instructions": "Lee el texto del puesto. ¿Dice que la jornada es tiempo completo? "
                        "Responde solo segun el texto.",
        "criteria": {"A": "el texto dice tiempo completo", "B": "no lo dice"},
    },
}

ESPERADO = {
    "dev_tele":     {"teletrabajo": "A", "licencia": "A", "anios_experiencia": "3a5", "jornada_tiempo_completo": "A"},
    "mecanico":     {"teletrabajo": "B", "licencia": "B", "anios_experiencia": "3a5", "jornada_tiempo_completo": "B"},
    "chofer":       {"teletrabajo": "B", "licencia": "A", "anios_experiencia": "1a2", "jornada_tiempo_completo": "A"},
}

ok = total = 0
for cname, state in CASOS.items():
    res = agent.predict(state, PREGUNTAS, max_len=8192)
    print(f"\n{cname}:")
    for q, a in res["answers"].items():
        esp = ESPERADO[cname][q]
        bien = a["choice"] == esp
        ok += bien
        total += 1
        print(f"   {q:24} -> {a['choice']:8} (esperado {esp:8}) {'OK' if bien else 'FALLA'}  {a.get('probabilities')}")
print(f"\nACIERTO: {ok}/{total}")
