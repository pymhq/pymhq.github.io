#!/usr/bin/env python3
"""
Generate innovation-cycles-card.svg -- a social-preview card for
/blog/2026/mlsys/ sized for LinkedIn/Twitter (1200x630, ~1.91:1).

The blog page keeps the full two-panel innovation_cycles diagram; this card is
a purpose-built hero: a bold title plus the Pattern-1 hype waves drawn large
with thick strokes and big labels, so it stays crisp after the platforms
downscale/recompress it. Run: python3 social_card.py
"""
import math

W, H = 1200, 630
L, R = 70, 980          # chart x range (room for right-side legend)
Y0, Y1 = 2016.0, 2026.5
TOP, BOT = 250, 560     # chart vertical band (title sits above)

def xpix(year):
    return L + (year - Y0) / (Y1 - Y0) * (R - L)

def ypix(v):
    return BOT - v * (BOT - TOP)

def gauss(x, mu, sig, amp):
    return amp * math.exp(-((x - mu) ** 2) / (2 * sig ** 2))

def logistic(x, x0, k, amp):
    return amp / (1.0 + math.exp(-(x - x0) / k))

def nlp(x):
    return gauss(x, 2019.3, 1.7, 0.82) + 0.10 * math.exp(-((x - 2024) ** 2) / 8)

def cloud(x):
    if x <= 2017.5:
        return gauss(x, 2017.5, 1.6, 0.90)
    return 0.90

LLM_SPIKES = [(2016.2, 0.32, 0.24), (2017.95, 0.26, 0.10), (2019.10, 0.28, 0.07)]

def llm(x):
    creep = 0.02 + 0.0010 * (x - Y0) ** 2
    spikes = sum(gauss(x, mu, sig, amp) for mu, sig, amp in LLM_SPIKES)
    return creep + spikes + logistic(x, 2022.7, 0.50, 0.80)

def poly(fn, step=0.04):
    pts = []
    x = Y0
    while x <= Y1 + 1e-9:
        pts.append((xpix(x), ypix(fn(x))))
        x += step
    d = "M {:.1f} {:.1f}".format(*pts[0])
    for p in pts[1:]:
        d += " L {:.1f} {:.1f}".format(*p)
    return d

C_NLP, C_CLOUD, C_LLM = "#e8923c", "#2f9e8f", "#5b6ee1"
INK, AXIS, GRID = "#222222", "#999999", "#ececec"

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
       f'font-family="Roboto, Helvetica, Arial, sans-serif">']
svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
svg.append(f'<rect x="0" y="0" width="{W}" height="10" fill="{C_LLM}"/>')

# ---- title block --------------------------------------------------------
svg.append(f'<text x="{L}" y="78" font-size="46" font-weight="700" fill="{INK}">'
           f'Three innovation cycles of the past decade</text>')
svg.append(f'<text x="{L}" y="118" font-size="23" fill="#666">'
           f'MLSys 2026 reading guide &#8212; NLP &#8594; Cloud Native &#8594; LLM / AI Native</text>')

# ---- horizontal legend --------------------------------------------------
lx = L
for color, label in [(C_NLP, "NLP / Conversational AI"),
                     (C_CLOUD, "Cloud Native"),
                     (C_LLM, "LLM / AI Native")]:
    svg.append(f'<line x1="{lx}" y1="170" x2="{lx+34}" y2="170" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
    svg.append(f'<text x="{lx+44}" y="176" font-size="20" fill="{INK}">{label}</text>')
    lx += 44 + len(label) * 11 + 40

# ---- chart axes ---------------------------------------------------------
for yr in [2016, 2018, 2020, 2022, 2024, 2026]:
    x = xpix(yr)
    svg.append(f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{BOT}" stroke="{GRID}" stroke-width="1.4"/>')
    svg.append(f'<text x="{x:.1f}" y="{BOT+28}" font-size="19" fill="#777" text-anchor="middle">{yr}</text>')
svg.append(f'<line x1="{L}" y1="{BOT}" x2="{R+30}" y2="{BOT}" stroke="{AXIS}" stroke-width="1.6"/>')
svg.append(f'<line x1="{L}" y1="{TOP-6}" x2="{L}" y2="{BOT}" stroke="{AXIS}" stroke-width="1.6"/>')

# ---- the three waves (thick) -------------------------------------------
for fn, color in [(nlp, C_NLP), (cloud, C_CLOUD), (llm, C_LLM)]:
    svg.append(f'<path d="{poly(fn)}" fill="none" stroke="{color}" stroke-width="5" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')

# peak notes
for yr, fn, color, note, anch in [(2017.5, cloud, C_CLOUD, "~2017–18", "middle"),
                                   (2019.3, nlp, C_NLP, "~2019–20", "middle"),
                                   (2016.2, llm, C_LLM, "AlphaGo ’16", "start"),
                                   (2026.2, llm, C_LLM, "rising", "end")]:
    cx, cy = xpix(yr), ypix(fn(yr))
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{color}"/>')
    tx = cx + (4 if anch == "start" else (-4 if anch == "end" else 0))
    svg.append(f'<text x="{tx:.1f}" y="{cy-10:.1f}" font-size="17" fill="{color}" '
               f'text-anchor="{anch}">{note}</text>')

# ---- footer -------------------------------------------------------------
svg.append(f'<text x="{R+30}" y="{H-22}" font-size="18" fill="#aaa" text-anchor="end">'
           f'pengandy.com/blog/2026/mlsys</text>')

svg.append('</svg>')

with open("innovation-cycles-card.svg", "w") as f:
    f.write("\n".join(svg))
print("wrote innovation-cycles-card.svg")
