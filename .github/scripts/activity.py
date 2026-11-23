"""Render the last year of contributions as a dot-matrix SVG in the bzuluaga.site palette.

Usage: GITHUB_TOKEN=... python .github/scripts/activity.py [login] [out.svg]
Standard library only, so it runs on a bare Actions runner.
"""
import base64, datetime, json, os, sys, urllib.request
from pathlib import Path

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "thezulux24"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "assets/activity.svg")
FONTS = Path(__file__).parent / "fonts"

VOID, TEXT, TEXT2, TEXT3, LINE = "#050a16", "#e8f2f6", "#adc1cd", "#8195a7", "#3e4e63"
CYAN, LIME, BLUE = "#28f7e4", "#b9f55d", "#50a0ff"

QUERY = """query($login:String!){user(login:$login){contributionsCollection{
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(json.dumps(data["errors"]))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days):
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        longest = max(longest, run)
    current = 0
    tail = list(reversed(days))
    if tail and not tail[0]["contributionCount"]:
        tail = tail[1:]  # today can still be empty without breaking the streak
    for d in tail:
        if not d["contributionCount"]:
            break
        current += 1
    return current, longest


def days_label(n):
    return f"{n} day" if n == 1 else f"{n} days"


def font_face(name):
    b64 = base64.b64encode((FONTS / f"{name}.woff").read_bytes()).decode()
    return f"@font-face{{font-family:'bz-{name}';src:url(data:font/woff;base64,{b64}) format('woff');}}"


def chamfer(w, h, c, o=0.5):
    return f"M{o + c},{o} H{w - o} V{h - o - c} L{w - o - c},{h - o} H{o} V{o + c} Z"


def render(cal):
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    total = cal["totalContributions"]
    current, longest = streaks(days)
    nonzero = sorted(d["contributionCount"] for d in days if d["contributionCount"])
    q = [nonzero[int(len(nonzero) * p)] if nonzero else 1 for p in (0.25, 0.5, 0.75)]

    def level(n):
        if not n:
            return 0
        return 1 + sum(n > t for t in q)

    W, H = 1280, 350
    X0, Y0 = 72, 160
    pitch = (W - 2 * X0) / (len(weeks) - 1) if len(weeks) > 1 else 20
    radius = [1.7, 3.4, 5.0, 6.6, 8.2]

    dots, months, last_month = [], [], None
    for wi, w in enumerate(weeks):
        x = X0 + wi * pitch
        for d in w["contributionDays"]:
            dow = datetime.date.fromisoformat(d["date"]).isoweekday() % 7
            y = Y0 + dow * pitch
            lv = level(d["contributionCount"])
            fill = f'fill="{LINE}"' if lv == 0 else 'fill="url(#foil)"'
            tip = f'{d["contributionCount"]} on {d["date"]}'
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius[lv]}" {fill}><title>{tip}</title></circle>')
        m = datetime.date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b").upper()
        if m != last_month and wi < len(weeks) - 2:
            if last_month is not None or w["contributionDays"][0]["date"][8:] <= "07":
                months.append(f'<text x="{x:.1f}" y="{Y0 + 6 * pitch + 40:.1f}" class="m">{m}</text>')
            last_month = m

    today = days[-1]
    tx = X0 + (len(weeks) - 1) * pitch
    ty = Y0 + (datetime.date.fromisoformat(today["date"]).isoweekday() % 7) * pitch

    css = (
        font_face("display") + font_face("sans") + font_face("mono")
        + f".m{{font:13px 'bz-mono';fill:{TEXT3};letter-spacing:1px}}"
        + ".ring{transform-origin:center;transform-box:fill-box;animation:ping 2.6s cubic-bezier(.23,1,.32,1) infinite}"
        + "@keyframes ping{0%{transform:scale(.6);opacity:.9}80%,100%{transform:scale(2.2);opacity:0}}"
        + "@media (prefers-reduced-motion:reduce){.ring{animation:none;opacity:0}}"
    )
    label = f"{total:,} contributions in the last year. Longest streak {days_label(longest)}, current streak {days_label(current)}."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">
<title>{label}</title><style>{css}</style>
<defs><linearGradient id="foil" x1="{X0}" y1="0" x2="{W - X0}" y2="0" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{BLUE}"/><stop offset=".5" stop-color="{CYAN}"/><stop offset="1" stop-color="{LIME}"/></linearGradient>
<clipPath id="c"><path d="{chamfer(W, H, 22, 0)}"/></clipPath></defs>
<rect width="{W}" height="{H}" fill="{VOID}" clip-path="url(#c)"/>
<path d="{chamfer(W, H, 22)}" fill="none" stroke="{LINE}"/>
<text x="{X0 - 8}" y="96" font-family="bz-display" font-size="64" fill="{TEXT}">{total:,}</text>
<text x="{X0 - 6}" y="128" font-family="bz-sans" font-size="20" fill="{TEXT2}">contributions in the last year</text>
<text x="{W - X0 + 8}" y="72" font-family="bz-mono" font-size="15" fill="{TEXT3}" text-anchor="end" letter-spacing="1.5">LONGEST STREAK <tspan fill="{TEXT}">{days_label(longest).upper()}</tspan></text>
<text x="{W - X0 + 8}" y="100" font-family="bz-mono" font-size="15" fill="{TEXT3}" text-anchor="end" letter-spacing="1.5">CURRENT STREAK <tspan fill="{CYAN}">{days_label(current).upper()}</tspan></text>
{''.join(dots)}
<circle class="ring" cx="{tx:.1f}" cy="{ty:.1f}" r="9" fill="none" stroke="{CYAN}" stroke-width="1.5"/>
{''.join(months)}
</svg>
"""


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(fetch()), encoding="utf-8")
    print(f"wrote {OUT}")
