"""Comprueba el estado de la sesión ANE en Brave (puerto 9222).

Sale con código 0 si hay sesión activa, 1 si no (para uso en run.bat).
"""
import sys

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://www.ane.cr/Puesto?Pagina=1", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(2000)
    href = pg.eval_on_selector_all(
        "a:has-text('Detalles del empleo')",
        "e => e.slice(0,2).map(x => x.getAttribute('href'))",
    )
    logged = bool(href) and href[0] != "/Cuenta/RegistroUsuario"
    print("LOGIN ACTIVO:", logged)
    print("hrefs:", href)
    print("cookies:", [c["name"] for c in ctx.cookies() if "ane.cr" in c["domain"]])
    b.close()
    sys.exit(0 if logged else 1)
