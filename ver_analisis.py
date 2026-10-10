import csv
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rows = list(csv.DictReader(open("salida/puestos_analizados.csv", encoding="utf-8-sig")))
print("cols:", list(rows[0].keys())[-7:])
for r in rows:
    print(r["titulo"][:40], "| dec=", r["decision"], r["decision_confianza"],
          "| tele=", r["teletrabajo"], r["teletrabajo_confianza"],
          "| exig=", r["exigencia"], r["exigencia_valor"], r["exigencia_confianza"])
