"""Calibración 2: preguntas extractivas (la respuesta está literal en el texto)."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import laya  # noqa: E402

agent = laya.load("convaiinnovations/laya", subfolder="multilingual")

CASOS = {
    "dev_tele": {
        "titulo": "Desarrollador Backend Python",
        "descripcion": "Buscamos desarrollador Python con experiencia en APIs REST. "
                       "Modalidad teletrabajo, jornada tiempo completo. Proyecto indefinido.",
        "requisitos": "3 anos de experiencia con Python, ingles intermedio. Licencia B1.",
    },
    "mecanico": {
        "titulo": "Tecnico en Cabezotes",
        "descripcion": "Experiencia minima de 3 anos en rectificacion de asientos de valvulas. "
                       "Disponibilidad inmediata. Trabajo presencial en taller, San Jose.",
        "requisitos": "Secundaria tecnica completa. Sin licencia de conducir.",
    },
    "chofer": {
        "titulo": "Chofer Repartidor",
        "descripcion": "Reparto de mercaderia en ruta. Jornada diurna, tiempo completo.",
        "requisitos": "Licencia categoria B2 y B3 al dia. 2 anos de experiencia previa.",
    },
}

PREGUNTAS = {
    "teletrabajo": {
        "type": "choice",
        "instructions": "El texto menciona teletrabajo, trabajo remoto o trabajar desde casa?",
        "criteria": {"A": "si, el texto lo menciona", "B": "no, el texto no lo menciona"},
    },
    "licencia": {
        "type": "choice",
        "instructions": "El texto exige licencia de conducir?",
        "criteria": {"A": "si, pide licencia de conducir", "B": "no, no pide licencia"},
    },
    "anios_experiencia": {
        "type": "choice",
        "instructions": "Cuantos anos de experiencia pide el texto?",
        "criteria": {
            "ninguna": "no pide experiencia o dice sin experiencia",
            "1a2": "pide 1 o 2 anos",
            "3a5": "pide 3 a 5 anos",
            "mas5": "pide mas de 5 anos",
        },
    },
    "jornada_tiempo_completo": {
        "type": "choice",
        "instructions": "El texto indica jornada tiempo completo?",
        "criteria": {"A": "si", "B": "no o no lo indica"},
    },
}

for cname, state in CASOS.items():
    res = agent.predict(state, PREGUNTAS, max_len=8192)
    print(f"\n{cname}:")
    for q, a in res["answers"].items():
        print(f"   {q:24} -> {a['choice']:8} {a.get('probabilities')}")
