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
    by_year = {}
    for r in releases:
        y = r["published_at"][:4]
        by_year[y] = by_year.get(y, 0) + sum(a["download_count"] for a in r["assets"])
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
        "by_year": dict(sorted(by_year.items())),
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
    # Sampled from the jdkato.io story cards.
    "light": dict(bg="#f4f2ea", rule="#e3e1d9", text="#1a1a1a", muted="#6f6d66", accent="#e87ba4", quiet="#efc2ce"),
    "dark": dict(bg="#1a1a1c", rule="#333236", text="#f4f2ea", muted="#a4a29a", accent="#e87ba4", quiet="#5a3a48"),
}
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def svg(stats, t):
    w, h, pad = 760, 320, 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Vale by the numbers">',
        "<title>Vale by the numbers</title>",
        f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>',
        # kicker
        f'<rect x="{pad}" y="{pad-1}" width="14" height="14" fill="{t["accent"]}"/>',
        f'<text x="{pad+24}" y="{pad+11}" font-family="{MONO}" font-size="12" font-weight="700" '
        f'letter-spacing="0.18em" fill="{t["text"]}">JDKATO<tspan fill="{t["muted"]}"> · VALE</tspan></text>',
        f'<text x="{w-pad}" y="{pad+11}" text-anchor="end" font-family="{MONO}" font-size="11" '
        f'letter-spacing="0.08em" fill="{t["muted"]}">UPDATED {stats["updated"]}</text>',
        # hero
        f'<text x="{pad-2}" y="{pad+92}" font-family="{SANS}" font-size="72" font-weight="800" font-style="italic" '
        f'letter-spacing="-0.03em" fill="{t["text"]}">{compact(stats["downloads"])} DOWNLOADS</text>',
        f'<text x="{pad}" y="{pad+120}" font-family="{SANS}" font-size="16" fill="{t["muted"]}">'
        f'GitHub releases and Docker Hub pulls of the Vale CLI since 2017.</text>',
    ]
    # secondary stats row
    row = [
        (compact(stats["vale_stars"]), "stars"),
        (compact(stats["vscode_installs"]), "VS Code installs"),
        (compact(stats["brew_installs_365d"]), "Homebrew installs / yr"),
        (str(stats["releases"]), "releases"),
    ]
    y = pad + 168
    x = pad
    for value, label in row:
        parts += [
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="22" font-weight="700" fill="{t["text"]}">{value}</text>',
            f'<text x="{x}" y="{y+18}" font-family="{SANS}" font-size="12" fill="{t["muted"]}">{label}</text>',
        ]
        x += 170
    # rule + year strip
    ry = h - 78
    parts.append(f'<line x1="{pad}" y1="{ry}" x2="{w-pad}" y2="{ry}" stroke="{t["rule"]}"/>')
    years = list(stats["by_year"].items())
    peak = max(v for _, v in years) or 1
    bw, gap, maxh = 22, 6, 34
    base = h - pad + 2
    peak_year = max(years, key=lambda kv: kv[1])[0]
    for i, (year, n) in enumerate(years):
        bh = max(2, round(maxh * n / peak))
        x = pad + i * (bw + gap)
        fill = t["accent"] if year == peak_year else t["quiet"]
        parts.append(f'<rect x="{x}" y="{base-bh}" width="{bw}" height="{bh}" fill="{fill}"><title>{year}: {n:,} downloads</title></rect>')
    first, last = years[0][0], years[-1][0]
    strip_w = len(years) * (bw + gap) - gap
    parts += [
        f'<text x="{pad}" y="{base+14}" font-family="{MONO}" font-size="10" fill="{t["muted"]}">{first}</text>',
        f'<text x="{pad+strip_w}" y="{base+14}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["muted"]}">{last}</text>',
        f'<text x="{pad+strip_w+16}" y="{base-4}" font-family="{SANS}" font-size="12" fill="{t["muted"]}">'
        f'downloads by release year · peak {peak_year}, {compact(peak)}</text>',
        f'<text x="{w-pad}" y="{base-2}" text-anchor="end" font-family="{MONO}" font-size="13" font-weight="700" '
        f'letter-spacing="0.06em" fill="{t["muted"]}">jdkato.io</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def essays(limit=2):
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
    out = out[:limit]
    for e in out:
        e["image"] = og_image(e["link"])
    return out


def og_image(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jdkato-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    return m.group(1) if m else url.rstrip("/").replace("/stories/", "/og/") + ".png"


def splice(text, name, body):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README is missing the {name} markers")
    return pattern.sub(f"{start}\n{body}\n{end}", text)


def update_readme(stats, posts):
    text = open(README).read()
    cells = "".join(
        f'<a href="{p["link"]}"><img src="{p["image"]}" alt="{escape(p["title"], quote=True)}" width="49%"></a>\n'
        for p in posts
    )
    text = splice(text, "essays", f'<p align="center">\n{cells}</p>')
    open(README, "w").write(text)


def main():
    stats = collect()
    os.makedirs(OUT, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(OUT, f"stats-{name}.svg"), "w") as f:
            f.write(svg(stats, theme))
    update_readme(stats, essays())
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    sys.exit(main())
