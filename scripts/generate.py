ligne1
    ligne2 "x" é
#!/usr/bin/env python3
"""Génère profile.svg : contributions et statistiques GitHub.

Usage :
  GH_TOKEN=... GH_LOGIN=Matar18 python scripts/generate.py   # vraies données
  python scripts/generate.py --demo                          # aperçu (données fictives)
"""
import datetime as dt
import html
import json
import os
import random
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGIN = os.environ.get("GH_LOGIN", "Matar18")
HANDLE = "matar"
MONTHS = ["jan", "fév", "mar", "avr", "mai", "jun", "jul", "aoû", "sep", "oct", "nov", "déc"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

# Palette GitHub (thème sombre)
BG, BORDER, PANEL = "#0d1117", "#30363d", "#161b22"
TEXT, MUTED, BLUE = "#c9d1d9", "#8b949e", "#58a6ff"
GREENS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"


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
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"], LEVELS[d["contributionLevel"]])
            for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "days": days,
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "repos": u["repositories"]["totalCount"],
    }


def demo():
    rnd = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=today.isoweekday() % 7 + 52 * 7)
    days = []
    for i in range((today - start).days + 1):
        d = start + dt.timedelta(days=i)
        c = 0 if rnd.random() < 0.3 else int(rnd.expovariate(1 / 4)) + 1
        days.append((d, c, 0))
    mx = max(c for _, c, _ in days)
    days = [(d, c, 0 if c == 0 else min(4, 1 + int(4 * c / (mx + 1)))) for d, c, _ in days]
    total = sum(c for _, c, _ in days)
    return {"days": days, "total": total, "commits": int(total * 0.8), "prs": 42, "repos": 18}


def stats(data):
    days = data["days"]
    today = days[-1][0]
    # Série actuelle : on ne pénalise pas la journée en cours si elle est encore vide
    i = len(days) - 1
    if days[i][1] == 0:
        i -= 1
    streak = 0
    while i >= 0 and days[i][1] > 0:
        streak += 1
        i -= 1
    active = sum(1 for _, c, _ in days if c > 0)
    # Contributions par mois (12 derniers mois, mois en cours inclus)
    months = []
    y, m = today.year, today.month
    for _ in range(12):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()
    per = {k: 0 for k in months}
    for d, c, _ in days:
        if (d.year, d.month) in per:
            per[(d.year, d.month)] += c
    return streak, active, [(MONTHS[m - 1], per[(y, m)]) for y, m in months]


def fmt(n):
    return f"{n:,}".replace(",", "\u202f")


def prompt(x, y, cmd):
    return (f'<text x="{x}" y="{y}" class="mono" font-size="13">'
            f'<tspan fill="#3fb950">{HANDLE}@github</tspan><tspan fill="{BLUE}"> ~ </tspan>'
            f'<tspan fill="{TEXT}">$ {html.escape(cmd)}</tspan></text>')


def build(data):
    streak, active, monthly = stats(data)
    days = data["days"]
    W = 860
    out = []

    # --- Contributions (heatmap) ---------------------------------------------
    step, cell, gx, gy = 14, 11, 60, 100
    first = days[0][0]
    offset = first.isoweekday() % 7  # dimanche = 0, comme GitHub
    last_month = None
    for idx, (d, c, lvl) in enumerate(days):
        k = idx + offset
        col, row = divmod(k, 7)
        x, y = gx + col * step, gy + row * step
        out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{GREENS[lvl]}">'
                   f'<title>{d.isoformat()} : {c}</title></rect>')
        if row == 0 and d.month != last_month and d.day <= 7:
            out.append(f'<text x="{x}" y="{gy - 8}" class="mono muted" font-size="10">{MONTHS[d.month - 1]}</text>')
            last_month = d.month
    for row, lab in ((1, "lun"), (3, "mer"), (5, "ven")):
        out.append(f'<text x="24" y="{gy + row * step + 9}" class="mono muted" font-size="10">{lab}</text>')
    ly = gy + 7 * step + 20
    out.append(f'<text x="{gx}" y="{ly}" class="mono" font-size="12" fill="{TEXT}">'
               f'{fmt(data["total"])} contributions au cours des 12 derniers mois</text>')
    lx = W - 36 - 5 * step - 34
    out.append(f'<text x="{lx - 40}" y="{ly}" class="mono muted" font-size="10">moins</text>')
    for i, g in enumerate(GREENS):
        out.append(f'<rect x="{lx + i * step}" y="{ly - 10}" width="{cell}" height="{cell}" rx="2" fill="{g}"/>')
    out.append(f'<text x="{lx + 5 * step + 4}" y="{ly}" class="mono muted" font-size="10">plus</text>')

    # --- Tuiles de statistiques ---------------------------------------------
    sy = ly + 46
    out.append(prompt(24, sy - 6, "whoami --stats"))
    rx, rw = 24, W - 48
    gap, th = 12, 72
    tw = (rw - 5 * gap) / 6
    tiles = [
        (fmt(data["total"]), "contributions"),
        (fmt(data["commits"]), "commits"),
        (fmt(data["prs"]), "pull requests"),
        (fmt(data["repos"]), "dépôts publics"),
        (fmt(streak), "jours de série"),
        (fmt(active), "jours actifs"),
    ]
    ty = sy + 12
    for i, (v, lab) in enumerate(tiles):
        x = rx + i * (tw + gap)
        out.append(f'<rect x="{x:.1f}" y="{ty}" width="{tw:.1f}" height="{th}" rx="8" fill="{PANEL}" stroke="{BORDER}"/>')
        out.append(f'<text x="{x + 14:.1f}" y="{ty + 36}" class="mono" font-size="22" font-weight="700" fill="{GREENS[4]}">{v}</text>')
        out.append(f'<text x="{x + 14:.1f}" y="{ty + 57}" class="mono muted" font-size="11">{lab}</text>')

    # --- Histogramme mensuel -------------------------------------------------
    cy0 = ty + th + 40
    out.append(f'<text x="{rx}" y="{cy0}" class="mono muted" font-size="12">contributions / mois</text>')
    top, base = cy0 + 30, cy0 + 210
    out.append(f'<line x1="{rx}" y1="{base}" x2="{rx + rw}" y2="{base}" stroke="{BORDER}"/>')
    mx = max(v for _, v in monthly) or 1
    slot = rw / 12
    bw = 34
    for i, (lab, v) in enumerate(monthly):
        h = 0 if v == 0 else max(2, (base - top) * v / mx)
        x = rx + i * slot + (slot - bw) / 2
        col = GREENS[4] if i == 11 else GREENS[3]
        out.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw}" height="{h:.1f}" rx="3" fill="{col}">'
                   f'<title>{lab} : {v}</title></rect>')
        if v:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 5:.1f}" text-anchor="middle" class="mono muted" font-size="10">{v}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{base + 16}" text-anchor="middle" class="mono muted" font-size="10">{lab}</text>')
    art_bottom = base + 16

    # --- Pied ----------------------------------------------------------------
    fy = art_bottom + 36
    now = dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y")
    out.append(prompt(24, fy, ""))
    out.append(f'<rect x="{24 + 17 * 7.8 + 2:.0f}" y="{fy - 11}" width="8" height="14" fill="{GREENS[4]}"><animate attributeName="opacity" values="1;0" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/></rect>')
    out.append(f'<text x="{W - 24}" y="{fy}" text-anchor="end" class="mono muted" font-size="10">mis à jour le {now}</text>')
    H = fy + 22

    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Profil GitHub de {LOGIN}">',
        f'<style>.mono{{font-family:{MONO}}}.muted{{fill:{MUTED}}}'
        '</style>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
        f'<path d="M0.5 36 H{W - 0.5}" stroke="{BORDER}"/>',
        '<circle cx="22" cy="18" r="6" fill="#ff5f56"/><circle cx="42" cy="18" r="6" fill="#ffbd2e"/>'
        '<circle cx="62" cy="18" r="6" fill="#27c93f"/>',
        f'<text x="{W / 2}" y="22" text-anchor="middle" class="mono muted" font-size="12">{HANDLE}@github: ~</text>',
        prompt(24, 64, "contributions --last-year"),
    ]
    return "\n".join(head + out + ["</svg>"]) + "\n"


if __name__ == "__main__":
    data = demo() if "--demo" in sys.argv else fetch()
    path = os.path.join(ROOT, "profile.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build(data))
    print(f"OK : {path}")
