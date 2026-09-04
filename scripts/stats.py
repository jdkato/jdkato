#!/usr/bin/env python3
"""Regenerate the stats cards in ./assets from live public APIs.

Runs nightly via .github/workflows/stats.yml. No third-party dependencies.
"""
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape

GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "assets")
README = os.path.join(ROOT, "README.md")
FEED = "https://jdkato.io/rss.xml"


def get(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    req.add_header("User-Agent", "jdkato-profile-stats")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def gh(path):
    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"
    return get(f"https://api.github.com{path}", headers)


def gh_all(path):
    page, out = 1, []
    while True:
        chunk = gh(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        out.extend(chunk)
        if len(chunk) < 100:
            return out
        page += 1


def compact(n):
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f}M" if v < 10 else f"{v:.0f}M"
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.1f}K" if v < 10 else f"{v:.0f}K"
    return str(n)


def collect():
    vale = gh("/repos/vale-cli/vale")
    prose = gh("/repos/jdkato/prose")
    releases = gh_all("/repos/vale-cli/vale/releases")
    gh_downloads = sum(a["download_count"] for r in releases for a in r["assets"])
    first = min(r["published_at"] for r in releases)
    latest = max(releases, key=lambda r: r["published_at"])

    docker = get("https://hub.docker.com/v2/repositories/jdkato/vale/")["pull_count"]
    brew = get("https://formulae.brew.sh/api/formula/vale.json")["analytics"]["install"]["365d"]["vale"]

    vsx = get(
        "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json;api-version=3.0-preview.1",
        },
        data=json.dumps({
            "filters": [{"criteria": [{"filterType": 7, "value": "ChrisChinchilla.vale-vscode"}]}],
            "flags": 914,
        }).encode(),
    )
    vsx_installs = next(
        s["value"] for s in vsx["results"][0]["extensions"][0]["statistics"] if s["statisticName"] == "install"
    )

    years = (datetime.now(timezone.utc) - datetime.fromisoformat(first.replace("Z", "+00:00"))).days / 365.25
    return {
        "downloads": gh_downloads + docker,
        "gh_downloads": gh_downloads,
        "docker_pulls": docker,
        "brew_installs_365d": brew,
        "vscode_installs": int(vsx_installs),
        "vale_stars": vale["stargazers_count"],
        "prose_stars": prose["stargazers_count"],
        "releases": len(releases),
        "years": years,
        "latest_tag": latest["tag_name"],
        "latest_date": latest["published_at"][:10],
        "latest_url": latest["html_url"],
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


THEMES = {
    "light": dict(bg="#fcfcfb", border="#e4e3df", text="#0b0b0b", muted="#52514e", accent="#2a78d6"),
    "dark": dict(bg="#1a1a19", border="#333331", text="#ffffff", muted="#c3c2b7", accent="#3987e5"),
}


def svg(stats, t):
    tiles = [
        (compact(stats["downloads"]), "downloads", "GitHub + Docker Hub"),
        (compact(stats["vale_stars"]), "stars", "on vale-cli/vale"),
        (compact(stats["vscode_installs"]), "VS Code installs", "Vale Linter extension"),
        (compact(stats["brew_installs_365d"]), "Homebrew installs", "last 365 days"),
        (str(stats["releases"]), "releases", "since 2017"),
    ]
    w, h, pad = 760, 150, 24
    tile_w = (w - 2 * pad) / len(tiles)
    font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Vale by the numbers">',
        f'<title>Vale by the numbers</title>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<text x="{pad}" y="34" font-family="{font}" font-size="13" font-weight="600" fill="{t["muted"]}" '
        f'letter-spacing="0.06em">VALE BY THE NUMBERS</text>',
        f'<text x="{w-pad}" y="34" text-anchor="end" font-family="{font}" font-size="12" fill="{t["muted"]}">'
        f'updated {stats["updated"]}</text>',
    ]
    for i, (value, label, sub) in enumerate(tiles):
        x = pad + i * tile_w
        if i:
            parts.append(f'<line x1="{x:.1f}" y1="56" x2="{x:.1f}" y2="{h-pad}" stroke="{t["border"]}"/>')
        tx = x + (12 if i else 0)
        parts += [
            f'<text x="{tx:.1f}" y="92" font-family="{font}" font-size="34" font-weight="600" fill="{t["text"]}">{value}</text>',
            f'<text x="{tx:.1f}" y="111" font-family="{font}" font-size="13" fill="{t["text"]}">{label}</text>',
            f'<text x="{tx:.1f}" y="127" font-family="{font}" font-size="11" fill="{t["muted"]}">{sub}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)

def essays(limit=3):
    req = urllib.request.Request(FEED, headers={"User-Agent": "jdkato-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for item in root.iter("item"):
        out.append({
            "title": item.findtext("title"),
            "link": item.findtext("link"),
            "date": parsedate_to_datetime(item.findtext("pubDate")).strftime("%b %Y"),
            "blurb": item.findtext("description"),
        })
    return out[:limit]


TIMELINE = [
    ("2016", "Tombstone.js", "propositional logic"),
    ("2017", "Vale + prose", "prose linting, NLP in Go"),
    ("2019", "vale-action + packages", "CI and style guides"),
    ("2022", "vale-ls", "Vale in any editor"),
    ("2023", "Google Peer Bonus", "open source award"),
    ("2024", "Vale 3.0", "the current major"),
    ("2025", "Write Better with Vale", "the book"),
    ("2026", "agent-tools", "Vale for coding assistants"),
]


def timeline_svg(t):
    """Milestones on one line, labels staggered above and below so they never collide."""
    w, h, pad = 760, 150, 24
    n = len(TIMELINE)
    step = (w - 2 * pad) / (n - 1)
    y = h / 2 + 4
    font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Timeline, 2016 to 2026">',
        "<title>Timeline</title>",
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<line x1="{pad}" y1="{y}" x2="{w-pad}" y2="{y}" stroke="{t["border"]}" stroke-width="2"/>',
    ]
    for i, (year, title, sub) in enumerate(TIMELINE):
        x = pad + i * step
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        last = i == n - 1
        below = i % 2 == 0
        ys = (y + 22, y + 39, y + 55) if below else (y - 46, y - 29, y - 13)
        parts += [
            f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y + 10 if below else y - 10}" stroke="{t["border"]}"/>',
            f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{t["accent"] if last else t["bg"]}" stroke="{t["accent"]}" stroke-width="2"/>',
            f'<text x="{x:.1f}" y="{ys[0]}" text-anchor="{anchor}" font-family="{font}" font-size="11" font-weight="600" fill="{t["muted"]}">{year}</text>',
            f'<text x="{x:.1f}" y="{ys[1]}" text-anchor="{anchor}" font-family="{font}" font-size="12" font-weight="600" fill="{t["text"]}">{escape(title)}</text>',
            f'<text x="{x:.1f}" y="{ys[2]}" text-anchor="{anchor}" font-family="{font}" font-size="11" fill="{t["muted"]}">{escape(sub)}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)


def splice(text, name, body):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README is missing the {name} markers")
    return pattern.sub(f"{start}\n{body}\n{end}", text)


def update_readme(stats, posts):
    text = open(README).read()
    lines = []
    for p in posts:
        lines.append(f"* **[{p['title']}]({p['link']})** ({p['date']}). {p['blurb']}")
    text = splice(text, "essays", "\n".join(lines))
    text = splice(
        text,
        "release",
        f"* Shipping Vale. The latest release is [{stats['latest_tag']}]({stats['latest_url']}), "
        f"published {stats['latest_date']}.",
    )
    open(README, "w").write(text)


def main():
    stats = collect()
    os.makedirs(OUT, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(OUT, f"stats-{name}.svg"), "w") as f:
            f.write(svg(stats, theme))
        with open(os.path.join(OUT, f"timeline-{name}.svg"), "w") as f:
            f.write(timeline_svg(theme))
    update_readme(stats, essays())
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    sys.exit(main())
