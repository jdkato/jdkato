#!/usr/bin/env python3
"""Refresh the auto-updated blocks in README.md from public APIs.

Runs nightly via .github/workflows/stats.yml. No third-party dependencies.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape

GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "assets")
README = os.path.join(ROOT, "README.md")
FEED = "https://jdkato.io/rss.xml"
REPOS = ["vale-cli/vale", "vale-cli/vale-ls", "vale-cli/packages", "vale-cli/vale-action", "jdkato/prose"]


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
    releases = gh_all("/repos/vale-cli/vale/releases")
    gh_downloads = sum(a["download_count"] for r in releases for a in r["assets"])
    docker = get("https://hub.docker.com/v2/repositories/jdkato/vale/")["pull_count"]
    return {
        "downloads": gh_downloads + docker,
        "gh_downloads": gh_downloads,
        "docker_pulls": docker,
        "vale_stars": vale["stargazers_count"],
        "releases": len(releases),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def latest_releases(limit=4):
    out = []
    for repo in REPOS:
        try:
            r = gh(f"/repos/{repo}/releases/latest")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        out.append({
            "repo": repo,
            "name": repo.split("/")[1],
            "tag": r["tag_name"],
            "url": r["html_url"],
            "date": r["published_at"][:10],
        })
    out.sort(key=lambda r: r["date"], reverse=True)
    return out[:limit]


def essays(limit=4):
    req = urllib.request.Request(FEED, headers={"User-Agent": "jdkato-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for item in root.iter("item"):
        out.append({
            "title": item.findtext("title"),
            "link": item.findtext("link"),
            "date": parsedate_to_datetime(item.findtext("pubDate")).strftime("%b %Y"),
        })
    out = out[:limit]
    if out:
        out[0]["image"] = og_image(out[0]["link"])
    return out


def og_image(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jdkato-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    return m.group(1) if m else url.rstrip("/").replace("/stories/", "/og/") + ".png"


SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
THEMES = {
    "light": {"bg": "#f4f2ea", "ink": "#1a1a1a", "muted": "#77756e", "rule": "#d9d6cc"},
    "dark": {"bg": "#1c1b18", "ink": "#f4f2ea", "muted": "#9a978d", "rule": "#3a3833"},
}
SWATCH = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e05a8d", "#3a9b3a", "#8b7cf0"]


def banner(stats, theme):
    """Draw the header card in the same style as jdkato.io's summary page."""
    cells = [
        (compact(stats["downloads"]), "DOWNLOADS"),
        (compact(stats["vale_stars"]), "GITHUB STARS"),
        (str(stats["releases"]), "RELEASES"),
        ("2017", "MAINTAINING SINCE"),
    ]
    t = THEMES[theme]
    w, h = 1200, 418
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" rx="18" fill="{t["bg"]}"/>',
    ]
    for i, c in enumerate(SWATCH):
        out.append(f'<rect x="{64 + 12 * i}" y="58" width="12" height="12" fill="{c}"/>')
    out += [
        f'<text x="168" y="69" font-family="{MONO}" font-size="14" letter-spacing="3" fill="{t["muted"]}">JDKATO.IO  ·  VALE.SH</text>',
        f'<text x="1136" y="69" text-anchor="end" font-family="{MONO}" font-size="14" letter-spacing="3" fill="{t["muted"]}">AS OF {stats["updated"]}</text>',
        f'<line x1="64" y1="92" x2="1136" y2="92" stroke="{t["rule"]}" stroke-width="2"/>',
        f'<text x="60" y="196" font-family="{SANS}" font-size="96" font-weight="900" font-style="italic" letter-spacing="-4" fill="{t["ink"]}">JOSEPH KATO</text>',
        f'<text x="64" y="236" font-family="{MONO}" font-size="15" font-weight="700" letter-spacing="3" fill="{t["ink"]}">MATHEMATICIAN  ·  COMPUTATIONAL LINGUIST  ·  SOFTWARE DEVELOPER</text>',
        f'<rect x="64" y="272" width="1072" height="88" fill="none" stroke="{t["rule"]}" stroke-width="2"/>',
    ]
    step = 1072 / len(cells)
    for i, (value, label) in enumerate(cells):
        x = 64 + step * i
        if i:
            out.append(f'<line x1="{x:.0f}" y1="286" x2="{x:.0f}" y2="346" stroke="{t["rule"]}" stroke-width="2"/>')
        out += [
            f'<text x="{x + 24:.0f}" y="320" font-family="{SANS}" font-size="40" font-weight="900" font-style="italic" letter-spacing="-1.5" fill="{t["ink"]}">{value}</text>',
            f'<text x="{x + 24:.0f}" y="344" font-family="{MONO}" font-size="12" letter-spacing="2.5" fill="{t["muted"]}">{label}</text>',
        ]
    out.append("</svg>")
    return "\n".join(out) + "\n"


def splice(text, name, body):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README is missing the {name} markers")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def pretty(date):
    return datetime.strptime(date, "%Y-%m-%d").strftime("%b %-d, %Y")


def update_readme(stats, posts, releases):
    text = open(README).read()

    head = posts[0]
    block = (
        f'<a href="{head["link"]}"><img src="{head["image"]}" alt="{escape(head["title"], quote=True)}" width="100%"></a>\n\n'
        + "".join(f'- [{p["title"]}]({p["link"]}) <sub>{p["date"]}</sub>\n' for p in posts)
    ).rstrip()
    text = splice(text, "essays", block)

    block = "".join(
        f'- [{r["name"]}](https://github.com/{r["repo"]}) [{r["tag"]}]({r["url"]}) <sub>{pretty(r["date"])}</sub>\n'
        for r in releases
    ).rstrip()
    text = splice(text, "releases", block)

    open(README, "w").write(text)


def main():
    stats = collect()
    os.makedirs(OUT, exist_ok=True)
    update_readme(stats, essays(), latest_releases())
    for theme in THEMES:
        with open(os.path.join(OUT, f"banner-{theme}.svg"), "w") as f:
            f.write(banner(stats, theme))
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    sys.exit(main())
