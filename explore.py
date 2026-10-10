"""F2: Exploración vía CDP - verificar sesión ANE y descubrir selectores."""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = "https://www.ane.cr"
OUT = "checkpoints/exploracion.json"
result = {}

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    page.goto(f"{BASE}/Puesto?Pagina=1", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)

    html = page.content()
    result["logged_in_list"] = "/Cuenta/RegistroUsuario" not in html or "Cerrar sesión" in html or "Salir" in html
    result["title"] = page.title()

    # ¿A dónde apunta "Detalles del empleo"?
    links = page.eval_on_selector_all(
        "a:has-text('Detalles del empleo')",
        "els => els.slice(0,5).map(e => e.getAttribute('href'))"
    )
    result["detail_hrefs"] = links

    # Resultados encontrados / paginación
    try:
        result["resultados"] = page.inner_text("h3:has-text('Resultados encontrados')").strip()
    except Exception:
        result["resultados"] = None
    result["pagina_actual"] = page.inner_text(".pagination-container nav").strip()[:200] if page.query_selector(".pagination-container nav") else None

    # Campos de la primera tarjeta
    card = page.query_selector(".job-listing")
    if card:
        result["card_html"] = card.inner_html()[:3000]

    # Si hay sesión, abrir el primer detalle real
    real = [h for h in links if h and h != "/Cuenta/RegistroUsuario"]
    if real:
        page.goto(BASE + real[0], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        result["detail_url"] = real[0]
        result["detail_title"] = page.title()
        result["detail_body_text"] = page.inner_text("body")[:6000]
        result["detail_html_snippet"] = page.content()[:12000]
    else:
        result["detail_url"] = None
        result["note"] = "Sin sesion: 'Detalles del empleo' apunta a /Cuenta/RegistroUsuario"

    browser.close()

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("logged_in_list:", result["logged_in_list"])
print("detail_hrefs:", result["detail_hrefs"])
print("resultados:", result["resultados"])
print("detail_url:", result.get("detail_url"))
print("Guardado en", OUT)
