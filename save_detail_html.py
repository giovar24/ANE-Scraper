"""F2b: guarda el HTML de 2 páginas de detalle para fijar selectores."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://www.ane.cr"
Path("checkpoints/html").mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()

    pg.goto(f"{BASE}/Puesto?Pagina=1", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(1500)
    hrefs = pg.eval_on_selector_all(
        "a[href*='/Puesto/Detalles']", "e => e.map(x => x.getAttribute('href'))"
    )
    print("detalles en pagina 1:", len(hrefs))

    for i, h in enumerate(dict.fromkeys(hrefs)):
        if i >= 2:
            break
        pg.goto(BASE + h, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(1500)
        pid = h.split("=")[-1]
        Path(f"checkpoints/html/detalle_{pid}.html").write_text(pg.content(), encoding="utf-8")
        # Localizar el contenedor principal
        main = pg.query_selector("#Detalles, .detalles, .job-detalle, .section.job-details, main")
        print(h, "->", "main:", bool(main))
    b.close()
print("OK")
