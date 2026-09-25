#!/usr/bin/env python3
"""
Demo video generator — redesigned v2.

Each 8-second video shows the actual processing flow:
  0.0s–1.5s  Input file data preview (styled HTML)
  1.5s–3.2s  Browser UI: file selected, process type chosen
  3.2s–4.5s  Browser UI: processing / success state
  4.5s–8.0s  Output file data preview (styled HTML)

White background. Romanian only. NextUP badge. Amber/teal contrast.
"""

import os, sys, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from playwright.sync_api import sync_playwright

DEMO_DIR = Path(__file__).resolve().parent
INPUTS  = DEMO_DIR / "inputs"
OUTPUTS = DEMO_DIR / "outputs"
VIDEOS  = DEMO_DIR / "videos"
VIDEOS.mkdir(parents=True, exist_ok=True)

# ── Server management ───────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 5000

def _server_running():
    import socket
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect((HOST, PORT))
        s.close()
        return True
    except Exception:
        return False

def _ensure_server():
    """Start Flask server in background if not running."""
    if _server_running():
        return None  # already running
    import subprocess as sp
    proc = sp.Popen(
        [sys.executable, str(ROOT / "app" / "server.py")],
        stdout=sp.DEVNULL, stderr=sp.DEVNULL,
    )
    # Wait for startup
    for _ in range(20):
        time.sleep(0.3)
        if _server_running():
            return proc
    proc.kill()
    raise RuntimeError("Server did not start in time")

# ── Colour palette ──────────────────────────────────────────────────────
BG       = "#fafaf9"
TEXT     = "#1a1a2e"
MUTED    = "#78716c"
AMBER    = "#d97706"
AMBER_LT = "#fef3c7"
RED_HL   = "#dc2626"
RED_BG   = "#fef2f2"
TEAL     = "#0d9488"
TEAL_LT  = "#ccfbf1"
GREEN_HL = "#16a34a"
GREEN_BG = "#f0fdf4"
BORDER   = "#e7e5e4"
CARD_BG  = "#ffffff"

# ── Modules ─────────────────────────────────────────────────────────────
MODULES = [
    {
        "id": "borderou", "nume": "Borderou de Vânzare",
        "tip_procesare": "borderou",
        "caption1": "Borderou de Vânzare → import NextUP în 5 secunde",
        "caption2": "53 de coloane, TVA separat, conturi completate automat",
        "accent": "Seria BFM1 0014 extrasă automat din câmpul Explicații",
        "f_in":  INPUTS / "Borderou_de_Vanzare_M1_demo.xlsx",
        "f_out": OUTPUTS / "borderou - Borderou_de_Vanzare_(M1).xlsx",
        "hl_before": {"Explicatii"},
        "hl_after":  {"Serie document", "Cota TVA", "Cont casa"},
        "badge": "NextUP · 53 coloane",
    },
    {
        "id": "cardcec", "nume": "Plăți POS",
        "tip_procesare": "cardcec",
        "caption1": "Export POS → jurnal de casă NextUP în 5 secunde",
        "caption2": "CARD → 51131, CEC → 51132, TICHET → 53281. Valori negate.",
        "accent": "Date formatate YYYYMMDD. Diacritice normalizate automat.",
        "f_in":  INPUTS / "Incasari_POS_Autoservire_demo.xlsx",
        "f_out": OUTPUTS / "cardcec_autoservire_out.xlsx",
        "hl_before": {"Tip Incasare", "Data Ultimei Incasari"},
        "hl_after":  {"Cont credit simbol", "Valoare", "Data"},
        "badge": "NextUP · 53 coloane",
    },
    {
        "id": "sgr", "nume": "Garanții SGR RetuRO",
        "tip_procesare": "sgr",
        "caption1": "PDF text RetuRO → înregistrare NextUP în 5 secunde",
        "caption2": "Text extras automat din PDF. An fiscal detectat din antet.",
        "accent": "6 vouchere extrase. Debit 53111. Credit 4621.",
        "f_in":  INPUTS / "Garantii_SGR_M1_demo.pdf",
        "f_out": OUTPUTS / "sgr_M1_out.xlsx",
        "hl_before": set(),
        "hl_after":  {"Cont debit simbol", "Cont credit simbol", "Explicatie"},
        "badge": "NextUP · 53 coloane",
        "pdf_input": True,
    },
    {
        "id": "avize", "nume": "Avize Ieșiri/Intrări",
        "tip_procesare": "avize",
        "caption1": "Avize → conturi 371.xx NextUP în 5 secunde",
        "caption2": "Cont per partener și per locație. TVA separat automat.",
        "accent": 'Număr partener extras din nume: „SC Demo SRL 1" → cont 371.19.1',
        "f_in":  INPUTS / "Iesiri avize M1 demo.xlsx",
        "f_out": OUTPUTS / "avize_M1_out.xlsx",
        "hl_before": {"Partener"},
        "hl_after":  {"Cont debit simbol", "Cont credit simbol"},
        "badge": "NextUP · 53 coloane",
    },
    {
        "id": "furnizori", "nume": "Centralizator Receptii",
        "tip_procesare": "furnizori",
        "caption1": "Recepții → import NextUP în 5 secunde",
        "caption2": "CUI curățat. Opțiune TVA detectată automat per rând.",
        "accent": '„RO12345678" → „12345678". TVA 0% → SCUTITE automat.',
        "f_in":  INPUTS / "Centralizator_Receptii_M1_demo.xlsx",
        "f_out": OUTPUTS / "furnizori_M1_out.xlsx",
        "hl_before": {"CUI/CNP"},
        "hl_after":  {"Cod fiscal", "Optiune TVA", "Denumire articol"},
        "badge": "NextUP · 43 coloane",
    },
    {
        "id": "adaos", "nume": "Adaos Comercial",
        "tip_procesare": "adaos",
        "caption1": "Fișier cu erori → sumar pe cote TVA în 5 secunde",
        "caption2": "Typo-uri ignorate. Sumar adăugat automat la final.",
        "accent": 'Antet greșit „TVVAaloare Diferenta" procesat fără eroare.',
        "f_in":  INPUTS / "Adaos_comercial_februarie_demo.xlsx",
        "f_out": OUTPUTS / "adaos_comercial_out.xlsx",
        "hl_before": {"TVVAaloare Diferenta", "% TVA VANZARE"},
        "hl_after":  {"% TVA VANZARE"},
        "badge": "NextUP · Excel cu sumar",
    },
    {
        "id": "sales", "nume": "Transformare Vânzări",
        "tip_procesare": "sales_transform",
        "caption1": "Export vânzări → import NextUP în 5 secunde",
        "caption2": "CLIENT MARFA eliminat. Doar clienți reali în output.",
        "accent": "7 rânduri → 6 rânduri. Rândul intern filtrat automat.",
        "f_in":  INPUTS / "Vanzari_gestiune_demo.xlsx",
        "f_out": OUTPUTS / "sales_transform_out.xlsx",
        "hl_before": {"tert"},
        "hl_after":  {"Nume partener", "Cod fiscal", "Serie"},
        "badge": "NextUP · 43 coloane",
    },
    {
        "id": "minus", "nume": "Valoare Negativă",
        "tip_procesare": "minus",
        "caption1": "Valori pozitive → negative. Date → YYYYMMDD.",
        "caption2": "Un click. Toate valorile negate. Toate datele corectate.",
        "accent": "1.250,50 → −1.250,50. 18-Mar-26 → 20260318.",
        "f_in":  INPUTS / "Minus_simple_demo.xlsx",
        "f_out": OUTPUTS / "minus_out.xlsx",
        "hl_before": {"Valoare", "Data Ultimei Incasari"},
        "hl_after":  {"Valoare", "Data Ultimei Incasari"},
        "badge": "NextUP · Format corectat",
    },
]


# ══════════════════════════════════════════════════════════════════════════
# HTML previews
# ══════════════════════════════════════════════════════════════════════════

def _esc(s: str) -> str:
    return s.replace("'", "'\\''").replace(":", "\\:").replace("%", "\\%")

def _build_html(m, side):
    """side = 'before' or 'after'"""
    is_before = (side == "before")
    fisier = m["f_in"] if is_before else m["f_out"]
    accent   = AMBER if is_before else TEAL
    accent_bg = AMBER_LT if is_before else TEAL_LT
    hl_text  = RED_HL if is_before else GREEN_HL
    hl_bg    = RED_BG if is_before else GREEN_BG
    label    = "ÎNAINTE" if is_before else "DUPĂ"
    highlights = m["hl_before"] if is_before else m["hl_after"]

    if m.get("pdf_input") and is_before:
        tbl = (
            '<div class="pdf-box"><pre>'
            'Plata Numerar    847  01/02/2026  Returnare garantie SGR   76,50\n'
            'Plata Voucher RetuRO  1735  02/02/2026  Returnare garantie SGR   6,00\n'
            'Plata Numerar    849  03/02/2026  Returnare garantie SGR  112,30\n'
            'Plata Voucher RetuRO  1741  04/02/2026  Returnare garantie SGR   3,50\n'
            'Plata Numerar    851  05/02/2026  Returnare garantie SGR   45,00\n'
            'Plata Voucher RetuRO  1752  06/02/2026  Returnare garantie SGR   8,00'
            '</pre></div>'
            '<p class="note">PDF fără tabele — doar linii de text</p>'
        )
    else:
        try:
            df = pd.read_excel(str(fisier))
            cols = [c for c in df.columns[:7]]
            df = df.head(7)[cols]
            rows = '<tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>'
            for _, row in df.iterrows():
                cells = ''
                for c in cols:
                    v = str(row[c])[:45] if pd.notna(row[c]) else ''
                    cls = ' class="hl"' if c in highlights else ''
                    cells += f'<td{cls}>{v}</td>'
                rows += f'<tr>{cells}</tr>'
            tbl = f'<table>{rows}</table>'
        except Exception as e:
            tbl = f'<p class="err">{e}</p>'

    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{BG};color:{TEXT};font-family:'Segoe UI',Arial,sans-serif;
      display:flex;flex-direction:column;align-items:center;
      justify-content:center;min-height:100vh;padding:40px 60px}}
.badge{{display:inline-block;background:{accent};color:#fff;font-size:14px;
        font-weight:700;padding:5px 16px;border-radius:20px;letter-spacing:.5px;
        margin-bottom:12px}}
h1{{font-size:40px;font-weight:800;margin-bottom:4px;color:{TEXT}}}
.acc{{font-size:18px;color:{MUTED};margin-bottom:30px;max-width:700px;text-align:center;line-height:1.4}}
.label{{font-size:13px;font-weight:700;letter-spacing:1.5px;color:{accent};
        text-transform:uppercase;margin-bottom:6px}}
table{{border-collapse:collapse;width:100%;max-width:860px;background:{CARD_BG};
       border:1px solid {BORDER};border-radius:8px;overflow:hidden;
       box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
th{{background:{accent_bg};color:{accent};padding:10px 12px;text-align:left;
    font-size:13px;font-weight:700;border-bottom:2px solid {accent}}}
td{{padding:8px 12px;border-bottom:1px solid {BORDER};font-size:12px;color:{TEXT}}}
td.hl{{background:{hl_bg};color:{hl_text};font-weight:600}}
tr:last-child td{{border-bottom:none}}
.pdf-box{{background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
          padding:24px 30px;max-width:860px;width:100%;
          box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
.pdf-box pre{{font-family:'Cascadia Code',Consolas,monospace;font-size:13px;
              color:{TEXT};line-height:2.0;white-space:pre-wrap}}
.note{{color:{MUTED};font-size:14px;margin-top:16px;text-align:center}}
.err{{color:{RED_HL};font-size:14px}}
</style></head>
<body>
<span class="badge">{m['badge']}</span>
<p class="label">{label}</p>
<h1>{m['nume']}</h1>
<p class="acc">{m['accent']}</p>
{tbl}
</body></html>"""


# ══════════════════════════════════════════════════════════════════════════
# Screenshots
# ══════════════════════════════════════════════════════════════════════════

def _screenshot_html(pw, html, path, w, h):
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": w, "height": h})
    page.set_content(html, timeout=10000)
    page.wait_for_timeout(600)
    page.screenshot(path=str(path), full_page=False)
    page.close()
    browser.close()


def _capture_ui_flow(pw, module, tmp_dir, w, h):
    """
    Automate the web UI for one module.
    Returns list of screenshot paths: [file_selected, processing_done]
    """
    shots = []
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": w, "height": h})

    try:
        page.goto(f"http://{HOST}:{PORT}", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)

        # Upload file
        page.set_input_files('input[type="file"]', str(module["f_in"]))
        page.wait_for_timeout(400)

        # Select process type radio — click its label card (if exists)
        radio_selector = f'input[name="process_type"][value="{module["tip_procesare"]}"]'
        radio = page.locator(radio_selector)
        if radio.count() > 0:
            card = radio.locator("..")
            if card.count() > 0:
                card.first.click(force=True)
            else:
                radio.check(force=True)
            page.wait_for_timeout(300)

        # Screenshot 1: file uploaded + mode selected
        s1 = tmp_dir / f"{module['id']}_ui_select.png"
        page.screenshot(path=str(s1), full_page=False)
        shots.append(s1)

        # Click process, wait for download
        try:
            with page.expect_download(timeout=30000) as dl:
                page.locator('button#processBtn').click()
            dl.value  # download acknowledged
        except Exception as e:
            print(f"    [UI warn] download: {e}")
            page.wait_for_timeout(4000)

        page.wait_for_timeout(800)

        # Screenshot 2: post-processing (success message visible)
        s2 = tmp_dir / f"{module['id']}_ui_done.png"
        page.screenshot(path=str(s2), full_page=False)
        shots.append(s2)

    except Exception as e:
        print(f"    [UI fail] {module['id']}: {e}")
    finally:
        page.close()
        browser.close()

    return shots


# ══════════════════════════════════════════════════════════════════════════
# FFmpeg video assembly
# ══════════════════════════════════════════════════════════════════════════

def _make_video(before_png, ui_pngs, after_png, out_mp4, m, w, h):
    """
    8-second video with fade transitions between every segment.
    """
    TX = 0.35  # transition duration
    TARGET = 8.0

    fs = max(28, int(h * 0.028))
    fs_small = fs - 4
    y = h - fs - 48

    c1 = _esc(m["caption1"])
    c2 = _esc(m["caption2"])
    c3 = _esc(m["accent"])

    # Build segment durations (raw, before transition compensation)
    if ui_pngs:
        d = [1.6] + [1.8, 1.2][:len(ui_pngs)] + [3.4]
    else:
        d = [3.0, 5.0]

    # Extend last segment so total = TARGET (transitions eat TX per gap)
    n = len(d)
    gap_eat = (n - 1) * TX
    d[-1] += (TARGET + gap_eat) - sum(d)

    # Build ffmpeg inputs
    images = [before_png] + [str(u) for u in ui_pngs] + [after_png]
    flat = []
    for i, img in enumerate(images):
        flat += ["-loop", "1", "-t", f"{d[i]:.6f}", "-i", img]

    # Scale all inputs, then chain xfade transitions
    scale = ""
    for i in range(n):
        scale += (
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
        )

    # Chain xfades: [v0][v1]xfade → [f0]; [f0][v2]xfade → [f1]; ...
    xfade_chain = ""
    prev = "v0"
    cum = d[0]  # cumulative duration in output timeline
    for i in range(1, n):
        offset = cum - TX
        tag = f"f{i-1}"
        xfade_chain += (
            f"[{prev}][v{i}]xfade=transition=fade:duration={TX}:"
            f"offset={offset:.4f}[{tag}];"
        )
        cum = cum + d[i] - TX
        prev = tag

    # Caption timings: positions in output timeline
    before_end = d[0] - TX / 2
    # after_start = cumulative position when 'after' image begins
    if ui_pngs:
        after_start = d[0] + d[1] - 2 * TX + TX / 2
    else:
        after_start = d[0] - TX / 2
    cap2_end = min(after_start + 1.9, TARGET - 0.5)
    cap3_start = cap2_end

    filt = (
        f"{scale}{xfade_chain}"
        f"[{prev}]"
        f"drawtext=text='{c1}':fontsize={fs}:fontcolor=white:"
        f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.65:boxborderw=10:"
        f"enable='between(t,0,{before_end:.2f})',"
        f"drawtext=text='{c2}':fontsize={fs}:fontcolor=white:"
        f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.65:boxborderw=10:"
        f"enable='between(t,{after_start:.2f},{cap2_end:.2f})',"
        f"drawtext=text='{c3}':fontsize={fs_small}:fontcolor=#e5e5e5:"
        f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.55:boxborderw=8:"
        f"enable='between(t,{cap3_start:.2f},8)'"
        f"[outv]"
    )

    cmd = ["ffmpeg", "-y"] + flat + [
        "-filter_complex", filt,
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-r", "30",
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"    ffmpeg: {r.stderr[:300]}")
    return os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 800


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("ExcelProcessor  —  Generator Video Demo  (NextUP)")
    print("=" * 52)

    # Ensure server
    server_proc = _ensure_server()
    if server_proc:
        print("Server pornit automat.")
    else:
        print("Server deja activ.")
    time.sleep(0.5)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        with sync_playwright() as pw:
            for i, m in enumerate(MODULES, 1):
                mid = m["id"]
                print(f"[{i}/{len(MODULES)}] {m['nume']}")

                # Build HTML previews
                bf_html = _build_html(m, "before")
                af_html = _build_html(m, "after")

                for orient, w, h in [("v", 1080, 1920), ("h", 1920, 1080)]:
                    prefix = f"{mid}_{orient}"

                    # Screenshot HTML previews
                    bf_png = tmp / f"{prefix}_bf.png"
                    af_png = tmp / f"{prefix}_af.png"
                    _screenshot_html(pw, bf_html, bf_png, w, h)
                    _screenshot_html(pw, af_html, af_png, w, h)

                    # Capture UI flow
                    ui_shots = _capture_ui_flow(pw, m, tmp, w, h)

                    # Assemble video
                    out = VIDEOS / f"{mid}_vertical.mp4" if orient == "v" else VIDEOS / f"{mid}_horizontal.mp4"
                    ok = _make_video(bf_png, ui_shots, af_png, out, m, w, h)
                    sz = os.path.getsize(out) / 1024 if os.path.exists(out) else 0
                    label = "vertical" if orient == "v" else "orizontal"
                    print(f"  {label:<10} {'OK' if ok else 'FAIL'}  {sz:6.0f} KB")

    # Stop server if we started it
    if server_proc:
        server_proc.kill()
        print("\nServer oprit.")

    print("=" * 52)
    print("Finalizat. Fișiere video în demo/videos/")
    for f in sorted(VIDEOS.glob("*.mp4")):
        print(f"  {f.name}  ({os.path.getsize(f)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
