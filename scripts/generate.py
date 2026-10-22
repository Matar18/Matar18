#!/usr/bin/env python3
"""Génère header.svg (identité) et profile.svg (tableau de bord GitHub),
plus leurs variantes -light pour le thème clair.

  GH_TOKEN=... GH_LOGIN=Matar18 python scripts/generate.py   # vraies données
  python scripts/generate.py --demo                          # aperçu (données fictives)
"""
import datetime as dt
import html
import json
import math
import os
import random
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGIN = os.environ.get("GH_LOGIN", "Matar18")

# --- Identité (à modifier ici) ------------------------------------------------
NAME = "Matar N. KEITA"
TITLE = "Data Analyst & IA"
STACK = ["Python", "SQL", "Power BI", "Machine Learning"]

# --- Charte (thèmes sombre et clair) -----------------------------------------
THEMES = {
    "dark": dict(BG="#0d1117", PANEL="#161b22", LINE="#21262d", BORDER="#30363d", TEXT="#e6edf3", SOFT="#c9d1d9",
                 MUTED="#8b949e", DIM="#6e7681", GREEN="#3fb950", GREEN2="#2ea043", GLOW=".28", HAREA=".45", AREA=".35"),
    "light": dict(BG="#ffffff", PANEL="#f6f8fa", LINE="#d8dee4", BORDER="#d0d7de", TEXT="#1f2328", SOFT="#31373d",
                  MUTED="#59636e", DIM="#818b98", GREEN="#1a7f37", GREEN2="#2da44e", GLOW=".14", HAREA=".28", AREA=".22"),
}


def use(theme):
    globals().update(THEMES[theme])


use("dark")
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
W = 860

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN manquant (ou utilisez --demo).")
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-card"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        sys.exit(f"Erreur GraphQL : {data['errors']}")
    u = data["data"]["user"]
    cc = u["contributionsCollection"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "days": days,
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "issues": cc["totalIssueContributions"],
        "repos": u["repositories"]["totalCount"],
    }


def demo():
    rnd = random.Random(3)
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i), 0 if rnd.random() < 0.45 else rnd.randint(1, 6)) for i in range(370)][::-1]
    total = sum(c for _, c in days)
    return {"days": days, "total": total, "commits": int(total * .7), "prs": 48, "reviews": 21,
            "issues": 9, "repos": 12}


# --- Outils -------------------------------------------------------------------
def fmt(n):
    return f"{n:,}".replace(",", "\u202f")


def esc(s):
    return html.escape(str(s))


def text(x, y, s, size=12, fill=None, weight=400, anchor="start", family="sans", extra=""):
    fill = fill or TEXT
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS if family == "sans" else MONO}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def smooth(pts):
    """Courbe monotone (Fritsch-Carlson) : pas de dépassement sous la ligne de base."""
    n = len(pts)
    if n < 2:
        return ""
    dx = [pts[i + 1][0] - pts[i][0] for i in range(n - 1)]
    m = [(pts[i + 1][1] - pts[i][1]) / dx[i] for i in range(n - 1)]
    t = [m[0]] + [0 if m[i - 1] * m[i] <= 0 else (m[i - 1] + m[i]) / 2 for i in range(1, n - 1)] + [m[-1]]
    for i in range(n - 1):
        if m[i] == 0:
            t[i] = t[i + 1] = 0
        else:
            a, b = t[i] / m[i], t[i + 1] / m[i]
            s = a * a + b * b
            if s > 9:
                k = 3 / math.sqrt(s)
                t[i], t[i + 1] = k * a * m[i], k * b * m[i]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n - 1):
        (x0, y0), (x1, y1), h = pts[i], pts[i + 1], dx[i] / 3
        d += f" C{x0 + h:.1f},{y0 + t[i] * h:.1f} {x1 - h:.1f},{y1 - t[i + 1] * h:.1f} {x1:.1f},{y1:.1f}"
    return d


def svg(h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'role="img" aria-label="{esc(label)}">\n' + "\n".join(body) + "\n</svg>\n")


# --- En-tête ------------------------------------------------------------------
def header():
    H = 230
    b = [
        '<defs>',
        f'<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.1" fill="{BORDER}"/></pattern>',
        f'<radialGradient id="glow" cx="78%" cy="45%" r="55%"><stop offset="0" stop-color="{GREEN2}" stop-opacity="{GLOW}"/>'
        f'<stop offset="1" stop-color="{GREEN2}" stop-opacity="0"/></radialGradient>',
        f'<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{BG}"/><stop offset=".55" stop-color="{BG}" stop-opacity=".2"/>'
        f'<stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient>',
        f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="{HAREA}"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>',
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>',
        '</defs>',
        f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{BG}"/>'
        f'<rect width="{W}" height="{H}" fill="url(#dots)"/><rect width="{W}" height="{H}" fill="url(#glow)"/>'
        f'<rect width="{W}" height="{H}" fill="url(#fade)"/></g>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="{BORDER}"/>',
    ]
    # Motif graphique (décoratif)
    vals = [14, 22, 18, 29, 25, 37, 33, 44, 40, 52, 49, 61]
    x0, x1, y0, y1 = 560, 812, 60, 178
    step = (x1 - x0) / (len(vals) - 1)
    pts = [(x0 + i * step, y1 - (y1 - y0) * v / 64) for i, v in enumerate(vals)]
    for i, (x, y) in enumerate(pts):
        b.append(f'<rect x="{x - 5:.1f}" y="{y + 8:.1f}" width="10" height="{y1 - y - 8:.1f}" rx="2" fill="{GREEN}" opacity="{.06 + .012 * i:.3f}"/>')
    for gy in (y0, (y0 + y1) / 2, y1):
        b.append(f'<line x1="{x0 - 12}" y1="{gy:.1f}" x2="{x1 + 12}" y2="{gy:.1f}" stroke="{LINE}" stroke-dasharray="2 5"/>')
    path = smooth(pts)
    b.append(f'<path d="{path} L{pts[-1][0]:.1f},{y1} L{pts[0][0]:.1f},{y1} Z" fill="url(#area)"/>')
    b.append(f'<path d="{path}" fill="none" stroke="{GREEN}" stroke-width="2.5" stroke-linecap="round"/>')
    lx, ly = pts[-1]
    b.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="9" fill="{GREEN}" opacity=".18"/><circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="{GREEN}"/>')
    # Identité
    b.append(f'<circle cx="52" cy="58" r="4" fill="{GREEN}"/>')
    b.append(text(64, 62, f"github.com/{LOGIN}", 12, MUTED, family="mono"))
    b.append(text(46, 118, NAME, 46, TEXT, 700, extra='letter-spacing="-0.5"'))
    b.append(text(48, 152, TITLE, 20, GREEN, 600))
    x = 48
    for s in STACK:
        w = 22 + len(s) * 7.1
        b.append(f'<rect x="{x}" y="172" width="{w:.1f}" height="28" rx="14" fill="{PANEL}" stroke="{BORDER}"/>')
        b.append(text(x + w / 2, 190.5, s, 12.5, SOFT, 500, "middle"))
        x += w + 10
    return svg(H, b, f"{NAME} — {TITLE}")


# --- Tableau de bord ----------------------------------------------------------
def dashboard(data):
    days = data["days"]
    i = len(days) - 1
    if days[i][1] == 0:
        i -= 1
    streak = 0
    while i >= 0 and days[i][1] > 0:
        streak += 1
        i -= 1
    active = sum(1 for _, c in days if c > 0)
    weeks = {}
    for d, c in days:
        k = d - dt.timedelta(days=d.isoweekday() % 7)
        weeks[k] = weeks.get(k, 0) + c
    weekly = sorted(weeks.items())[-26:]

    H = 446
    now = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y")
    b = [
        '<defs>',
        f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="{AREA}"/>'
        f'<stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>',
        f'<linearGradient id="bar" x1="0" x2="1"><stop offset="0" stop-color="{GREEN2}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>',
        '</defs>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="{BG}" stroke="{BORDER}"/>',
        f'<circle cx="34" cy="37" r="4" fill="{GREEN}"/>',
        text(46, 41, "ACTIVITÉ GITHUB", 11, MUTED, 600, extra='letter-spacing="1.6"'),
        text(W - 28, 41, f"12 derniers mois · mis à jour le {now}", 11, DIM, anchor="end"),
    ]

    # Indicateurs
    tiles = [("Contributions", data["total"]), ("Commits", data["commits"]), ("Pull requests", data["prs"]),
             ("Dépôts publics", data["repos"]), ("Jours actifs", active)]
    gap, ty, th = 14, 62, 100
    tw = (W - 56 - gap * (len(tiles) - 1)) / len(tiles)
    for k, (lab, v) in enumerate(tiles):
        x = 28 + k * (tw + gap)
        b.append(f'<rect x="{x:.1f}" y="{ty}" width="{tw:.1f}" height="{th}" rx="12" fill="{PANEL}" stroke="{LINE}"/>')
        b.append(f'<rect x="{x + 18:.1f}" y="{ty + 18}" width="18" height="3" rx="1.5" fill="{GREEN}"/>')
        b.append(text(x + 18, ty + 44, lab.upper(), 10.5, MUTED, 600, extra='letter-spacing="1"'))
        b.append(text(x + 18, ty + 82, fmt(v), 30, TEXT, 700, extra='letter-spacing="-0.5"'))

    # Panneau : contributions par semaine
    py, ph = ty + th + 14, 242
    px, pw = 28, 500
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="{PANEL}" stroke="{LINE}"/>')
    b.append(text(px + 22, py + 34, "Contributions par semaine", 14, TEXT, 600))
    b.append(text(px + 22, py + 54, f"26 dernières semaines · série actuelle : {streak} jour{'s' if streak > 1 else ''}", 11.5, MUTED))
    cx0, cx1, cy0, cy1 = px + 22, px + pw - 22, py + 78, py + 200
    mx = max([v for _, v in weekly] + [1])
    for g in range(3):
        gy = cy0 + (cy1 - cy0) * g / 2
        b.append(f'<line x1="{cx0}" y1="{gy:.1f}" x2="{cx1}" y2="{gy:.1f}" stroke="{LINE}" stroke-dasharray="{"" if g == 2 else "2 5"}"/>')
    b.append(text(cx1, cy0 - 6, f"max {mx}", 10, DIM, anchor="end"))
    stepx = (cx1 - cx0) / max(1, len(weekly) - 1)
    pts = [(cx0 + k * stepx, cy1 - (cy1 - cy0) * v / mx) for k, (_, v) in enumerate(weekly)]
    path = smooth(pts)
    b.append(f'<path d="{path} L{pts[-1][0]:.1f},{cy1} L{pts[0][0]:.1f},{cy1} Z" fill="url(#area)"/>')
    b.append(f'<path d="{path}" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    lx, ly = pts[-1]
    b.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="8" fill="{GREEN}" opacity=".18"/><circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="{GREEN}"/>')
    last_m, last_x = None, -99
    for k, (wk, _) in enumerate(weekly):
        x = pts[k][0]
        if wk.month != last_m and x - last_x > 34:
            b.append(text(x, cy1 + 22, MONTHS[wk.month - 1], 10.5, DIM, anchor="middle" if 0 < k < len(weekly) - 1 else "start"))
            last_m, last_x = wk.month, x
        last_m = wk.month

    # Panneau : répartition
    rx, rw = px + pw + 14, W - 28 - (px + pw + 14)
    b.append(f'<rect x="{rx}" y="{py}" width="{rw}" height="{ph}" rx="12" fill="{PANEL}" stroke="{LINE}"/>')
    b.append(text(rx + 22, py + 34, "Répartition", 14, TEXT, 600))
    b.append(text(rx + 22, py + 54, "par type de contribution", 11.5, MUTED))
    parts = [("Commits", data["commits"]), ("Pull requests", data["prs"]),
             ("Revues de code", data["reviews"]), ("Issues", data["issues"])]
    tot = sum(v for _, v in parts) or 1
    bw = rw - 44
    for k, (lab, v) in enumerate(parts):
        y = py + 92 + k * 38
        pct = round(100 * v / tot)
        b.append(text(rx + 22, y, lab, 12.5, SOFT, 500))
        b.append(text(rx + rw - 22, y, f"{pct} %", 12.5, TEXT, 600, "end"))
        b.append(f'<rect x="{rx + 22}" y="{y + 9}" width="{bw}" height="6" rx="3" fill="{LINE}"/>')
        if v:
            b.append(f'<rect x="{rx + 22}" y="{y + 9}" width="{max(6, bw * v / tot):.1f}" height="6" rx="3" fill="url(#bar)"/>')
    return svg(H, b, f"Activité GitHub de {LOGIN}")


if __name__ == "__main__":
    data = demo() if "--demo" in sys.argv else fetch()
    for theme, suffix in (("dark", ""), ("light", "-light")):
        use(theme)
        for name, content in ((f"header{suffix}.svg", header()), (f"profile{suffix}.svg", dashboard(data))):
            with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
                f.write(content)
    print("OK : header.svg, profile.svg (+ variantes -light)")
