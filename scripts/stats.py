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
            "blurb": item.findtext("description"),
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
        f'{escape(head["blurb"], quote=False)}\n\n'
        + "".join(f'- [{p["title"]}]({p["link"]}) <sub>{p["date"]}</sub>\n' for p in posts)
    ).rstrip()
    text = splice(text, "essays", block)

    block = "".join(
        f'- [{r["name"]}](https://github.com/{r["repo"]}) [{r["tag"]}]({r["url"]}) <sub>{pretty(r["date"])}</sub>\n'
        for r in releases
    ).rstrip()
    text = splice(text, "releases", block)

    line = (
        f'<sub>Vale so far: {compact(stats["downloads"])} downloads, {compact(stats["vale_stars"])} stars, '
        f'{stats["releases"]} releases since 2017.</sub>'
    )
    text = splice(text, "stats", line)
    open(README, "w").write(text)


def main():
    stats = collect()
    os.makedirs(OUT, exist_ok=True)
    update_readme(stats, essays(), latest_releases())
    with open(os.path.join(OUT, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    sys.exit(main())
