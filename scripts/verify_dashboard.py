"""In-browser verification of the dashboard: measure bar geometry, exercise the
interactive filters against the real DOM, surface any JS console errors, and
capture screenshots for the report."""
import re, json, sys
from playwright.sync_api import sync_playwright

URL = "file:///Users/sushaantshrestha/mba6418-assignment1/dashboard/index.html"
OUT = "/Users/sushaantshrestha/mba6418-assignment1/output"

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
    page.goto(URL)
    page.wait_for_load_state("networkidle")

    rows_data = page.evaluate(
        "Array.from(document.querySelectorAll('#tbody tr.row')).length")
    total_data = page.evaluate("RUNS[Object.keys(RUNS)[0]].rows.length")

    # ---- 1) bar geometry: no degenerate (zero/too-narrow) bars ----
    hbars = page.evaluate("""
        Array.from(document.querySelectorAll('.hbar-fill'))
             .map(b => ({w: Math.round(b.getBoundingClientRect().width),
                         pct: b.style.width}))
    """)
    vbars = page.evaluate("""
        Array.from(document.querySelectorAll('.vbar'))
             .map(b => ({h: Math.round(b.getBoundingClientRect().height),
                         style: b.style.height}))
    """)
    bad_w = [b for b in hbars if b["w"] < 2]
    bad_h = [b for b in vbars if b["h"] < 2]

    # ---- 2) interactive filters in the live DOM ----
    def count_line():
        return page.inner_text("#countLine")

    def t_rows():
        return page.evaluate("document.querySelectorAll('#tbody tr.row').length")

    checks = {}
    # mismatched
    page.click('#segFilter button[data-f="mismatch"]')
    checks["mismatch"] = (count_line(), t_rows())
    page.click('#segFilter button[data-f="all"]')
    # search 'gift'
    page.fill("#search", "gift")
    checks["search_gift"] = (count_line(), t_rows())
    page.fill("#search", "")
    # class NEGATIVE + mismatched combined
    page.select_option("#classFilter", "NEGATIVE")
    checks["class_neg"] = (count_line(), t_rows())
    page.click('#segFilter button[data-f="mismatch"]')
    checks["class_neg_mismatch"] = (count_line(), t_rows())
    # emotion filter joy
    page.click('#segFilter button[data-f="all"]')
    page.select_option("#classFilter", "all")
    page.select_option("#emoFilter", "joy")
    checks["emo_joy"] = (count_line(), t_rows())

    # expected counts straight from the embedded data (mirror of JS logic)
    expected = page.evaluate("""() => {
        const rows = RUNS[Object.keys(RUNS)[0]].rows;
        const ok = r => r.pred === r.correct;
        const m=(c='all',l='all',e='all',s='')=>rows.filter(r=>{
            if(c==='correct'&&!ok(r))return false;
            if(c==='mismatch'&&ok(r))return false;
            if(l!=='all'&&r.correct!==l)return false;
            if(e!=='all'&&r.llm_emotion!==e&&r.nrc_emotion!==e)return false;
            if(s&&!((r.title||'')+' '+(r.text||'')).toLowerCase().includes(s))return false;
            return true;}).length;
        return {
            mismatch: m('mismatch'),
            search_gift: m('all','all','all','gift'),
            class_neg: m('all','NEGATIVE'),
            class_neg_mismatch: m('mismatch','NEGATIVE'),
            emo_joy: m('all','all','joy')
        };
    }""")

    # ---- 3) layout: screenshot full page + light theme ----
    # switch to the Imbalanced 2-class tab and re-check a couple of filters
    page.click('.run-tab:text-is("Imbalanced 2-class")')
    page.wait_for_timeout(200)
    page.select_option("#classFilter", "all")
    page.select_option("#emoFilter", "all")
    page.fill("#search", "")
    page.click('#segFilter button[data-f="mismatch"]')
    im_mismatch = (count_line(), t_rows())
    page.click('#segFilter button[data-f="all"]')
    im_total = page.evaluate("RUNS['Imbalanced 2-class'].rows.length")

    page.screenshot(path=f"{OUT}/dashboard-dark.png",
                    full_page=True)
    page.click('button.theme-btn[data-var="light"]')
    page.screenshot(path=f"{OUT}/dashboard-light.png", full_page=True)
    page.click('button.theme-btn[data-var="sepia"]')
    page.screenshot(path=f"{OUT}/dashboard-sepia.png", full_page=True)

    # ---- report ----
    print("total data rows:", total_data, "| tbody rows rendered:", rows_data)
    print("\nHorizontal bars:", len(hbars), "| zero/tiny:", len(bad_w), bad_w[:4])
    print("Vertical bars:", len(vbars), "| zero/tiny:", len(bad_h), bad_h[:4])
    print("\nFilter checks (UI vs expected from data):")
    ok_all = True
    for k, (ui, exp) in [
        ("mismatch", (checks["mismatch"], expected["mismatch"])),
        ("search 'gift'", (checks["search_gift"], expected["search_gift"])),
        ("class NEGATIVE", (checks["class_neg"], expected["class_neg"])),
        ("NEGATIVE & mismatched", (checks["class_neg_mismatch"], expected["class_neg_mismatch"])),
        ("emotion joy", (checks["emo_joy"], expected["emo_joy"])),
    ]:
        ui_n = int(ui[0].split(" ")[1])
        match = ui_n == exp and ui[1] == exp
        ok_all = ok_all and match
        print(f"  {k:22} UI count={ui_n} UI rows={ui[1]} expected={exp}  {'OK' if match else 'MISMATCH'}")
    im_ok = im_mismatch[0].split(" ")[1] == "2" and im_mismatch[1] == 2 and im_total == 100
    ok_all = ok_all and im_ok
    print(f"  {'Imbalanced tab (2-class)':22} UI count={im_mismatch[0].split(' ')[1]} rows={im_mismatch[1]} total={im_total} expected 2 / 100  {'OK' if im_ok else 'MISMATCH'}")
    print("\nConsole/page errors:", len(errors))
    for e in errors[:10]:
        print("   ", e)
    print("\nRESULT:", "ALL CHECKS PASSED" if ok_all and not errors and not bad_w and not bad_h
          else "ISSUES FOUND")
    browser.close()
