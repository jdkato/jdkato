# Joseph Kato

[![Website](https://img.shields.io/badge/-jdkato.io-000?style=flat-square&logo=svelte&logoColor=ff3e00&color=f0f1f1)](https://jdkato.io) [![Vale](https://img.shields.io/badge/-vale.sh-000?style=flat-square&logo=go&logoColor=00ADD8&color=f0f1f1)](https://vale.sh) [![Email](https://img.shields.io/badge/-joseph@jdkato.io-c14438?style=flat-square&logo=Gmail&logoColor=BB001B&color=f0f1f1)](mailto:joseph@jdkato.io) [![Sponsor](https://img.shields.io/badge/-Sponsor-ea4aaa?style=flat-square&logo=githubsponsors&logoColor=ea4aaa&color=f0f1f1)](https://github.com/sponsors/jdkato) [![Vale lint](https://github.com/jdkato/jdkato/actions/workflows/main.yml/badge.svg)](https://github.com/jdkato/jdkato/actions/workflows/main.yml)

I'm Joseph. I make things and write about them.

Since 2017 that has meant [Vale](https://github.com/vale-cli/vale), a linter that treats prose like code, used by docs teams at AWS, Microsoft, GitLab, and Red Hat. Lately it means teaching Vale to work alongside coding assistants: [agent-tools](https://github.com/vale-cli/agent-tools) ships it as Claude Code skills, an edit-time hook, and an MCP server. Before that I wrote [prose](https://github.com/jdkato/prose), a Natural Language Processing library for Go.

On [jdkato.io](https://jdkato.io) I point the same habit at public data: how much arXiv abstracts hedge, who talks at Supreme Court oral argument, what 89,000 graded NBA calls say about referees, and whether vibe-coded pull requests actually burden maintainers.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stats-dark.svg">
  <img alt="Vale by the numbers: downloads, stars, VS Code installs, Homebrew installs, and releases." src="assets/stats-light.svg">
</picture>

<sub>Refreshed nightly by [`scripts/stats.py`](scripts/stats.py). Vale lints this README on every push.</sub>

#### ✍️ Latest essays

<!-- essays:start -->
* **[The hedge words of science](https://jdkato.io/stories/arxiv-hedging)** (Aug 2026). Scientists are trained to qualify their claims. Across 2,400 arXiv abstracts, how much a field hedges turns out to track something simpler than caution — whether it observes the world or proves things about it. And despite the reputation, hedging isn't on the rise.
* **[AI Tells: the burden of LLMs](https://jdkato.io/stories/github-ai-tells)** (Aug 2026). Codeberg's members just voted to ban vibe-coded projects, which is one way of saying the question has stopped being rhetorical. I build a prose linter, so I pointed it at a decade of GitHub instead — and the load turns out to be real, to land on pull requests rather than issues, and to look nothing like the tells everyone repeats.
<!-- essays:end -->

#### 🔭 Now

<!-- release:start -->
* Shipping Vale. The latest release is [v3.20.0](https://github.com/vale-cli/vale/releases/tag/v3.20.0), published 2026-09-02.
<!-- release:end -->
* Building [agent-tools](https://github.com/vale-cli/agent-tools), so prose linting happens inside coding assistants.

#### 🧰 The Vale ecosystem

| Project | What it does |
| --- | --- |
| [vale](https://github.com/vale-cli/vale) | The linter itself. Markup-aware, fast, and extensible. Written in Go. |
| [packages](https://github.com/vale-cli/packages) | Ready-made style guides: Microsoft, Google, IBM, write-good, proselint, and more. |
| [vale-ls](https://github.com/vale-cli/vale-ls) | A Language Server Protocol implementation, so Vale works in any editor. |
| [vale-action](https://github.com/vale-cli/vale-action) | The official GitHub Action. It lints this README on every push. |
| [agent-tools](https://github.com/vale-cli/agent-tools) | Skills, an edit-time hook, and an MCP server for coding assistants. |

Try it:

```sh
brew install vale && vale sync && vale README.md
```

#### 📌 Elsewhere

* **[Write Better with Vale][3]**, a Pragmatic Bookshelf title on automating style guides.
* **[Google Open Source Peer Bonus][1]** recipient, 2023.
* **[Appwrite OSS Fund][5]** grantee, one of twenty projects selected.
* Want to talk prose linting, docs tooling, or a data story? Email me.

[1]: https://opensource.googleblog.com/2023/05/google-open-source-peer-bonus-program-announces-first-group-of-winners-2023.html
[3]: https://pragprog.com/titles/bhvale/write-better-with-vale/
[5]: https://dev.to/appwrite/appwrite-oss-fund-sponsors-vale-4oig
