"""Calibración: prueba variantes de redacción en 2 casos conocidos."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import laya  # noqa: E402

agent = laya.load("convaiinnovations/laya", subfolder="multilingual")

PERFIL = ("Profesional con formacion en tecnologia y datos, buscando puesto de "
          "tiempo completo en Costa Rica, abierto a teletrabajo")

CASOS = {
    "ENCAJA (dev, teletrabajo)": {
        "titulo": "Desarrollador Backend Python",
        "empresa": "Tech Solutions",
        "descripcion": "Buscamos desarrollador Python con experiencia en APIs REST. "
                       "Modalidad teletrabajo, jornada tiempo completo. Proyecto indefinido.",
        "requisitos": "3 anos de experiencia con Python, ingles intermedio.",
    },
    "NO ENCAJA (mecanico presencial)": {
        "titulo": "Tecnico en Cabezotes",
        "empresa": "Importaciones GM",
        "descripcion": "Experiencia minima de 3 anos en rectificacion de asientos de "
                       "valvulas. Disponibilidad inmediata. Trabajo presencial en taller, "
                       "San Jose.",
        "requisitos": "Secundaria tecnica completa.",
    },
}

VARIANTES = {
    "v1_criterios_en_descripcion": {
        "decision": {
            "type": "choice",
            "instructions": "Este puesto le sirve al usuario? Perfil: {perfil}",
            "criteria": {
                "encaja": "el puesto coincide con la formacion en tecnologia y datos del perfil",
                "no_encaja": "el puesto no coincide con esa formacion ni condiciones",
            },
        }
    },
    "v2_si_no_neutro": {
        "decision": {
            "type": "choice",
            "instructions": "El puesto describido encaja con el perfil del usuario? "
                            "Perfil del usuario: {perfil}",
            "criteria": {
                "si": "si, el puesto encaja con el perfil",
                "no": "no, el puesto no encaja con el perfil",
            },
        }
    },
    "v3_lista_corta": {
        "decision": {
            "type": "choice",
            "instructions": "Dado el perfil del usuario, este puesto deberia estar en su "
                            "lista corta de vacantes a revisar? Perfil: {perfil}",
            "criteria": {
                "A": "si, incluirlo en la lista corta",
                "B": "no, dejarlo fuera",
                "C": "dudoso",
            },
        }
    },
}

for vname, preguntas in VARIANTES.items():
    preguntas["decision"]["instructions"] = preguntas["decision"]["instructions"].format(perfil=PERFIL)
    print(f"\n=== {vname} ===")
    for cname, state in CASOS.items():
        res = agent.predict(state, preguntas, max_len=8192)
        a = res["answers"]["decision"]
        probs = a.get("probabilities", {})
        print(f"  {cname:32} -> {a['choice']:10} probs={probs}")
