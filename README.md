# Issue Gate

GitHub issue forms and a chooser config that make "doesn't work" impossible to file without a reproduction. No dependencies, no API keys, no bot.

## Why

GitHub already ships this gate, for free: YAML issue forms plus `.github/ISSUE_TEMPLATE/config.yml` with `blank_issues_enabled: false`, which removes the blank-issue bypass. The problem is that nobody sets it up, and the default bug form GitHub ships has **Steps To Reproduce marked `required: false`** — so a useless report walks straight through the form and lands on a maintainer anyway.

Issue Gate writes those same native files with the fields that actually cost maintainer time marked required, prefills the environment block for the ecosystems your repo uses, and orders the contact links so questions get routed to docs, upstream, or Discussions instead of the tracker.

Nothing to install on the contributor's side. No bot. No AI.

## Used on

Running on our own public repos, merged as PRs:

- [danyblitz-bit/data-scraper](https://github.com/danyblitz-bit/data-scraper/pull/1) (Rust)
- [danyblitz-bit/site-auditor](https://github.com/danyblitz-bit/site-auditor/pull/1) (Python)
- [danyblitz-bit/pdf-metaclean](https://github.com/danyblitz-bit/pdf-metaclean/pull/1) (Python)
- [danyblitz-bit/photo-metaclean](https://github.com/danyblitz-bit/photo-metaclean/pull/1) (Python)

## Install & Run

No dependencies — Python 3.10+.

```bash
# See the diff, write nothing
python -m tools.issue-gate /path/to/repo --dry-run

# A Node library, questions routed to Discussions
python -m tools.issue-gate ~/code/my-lib --discussions

# Add contact links, then write
python -m tools.issue-gate ~/code/my-lib \
  --docs https://mylib.dev/docs \
  --upstream https://github.com/vendor/base-lib \
  --discussions

# Print the generated files in full
python -m tools.issue-gate ~/code/my-lib --verbose

# Verify the tool works on your machine
python -m tools.issue-gate --self-check
```

Then push and open `/issues/new/choose` on the repo to see the gate.

## Options

| Flag | Description |
|------|-------------|
| `--docs URL` | Add a Documentation contact link (first in the chooser) |
| `--upstream URL` | Add an Upstream project contact link (for wrappers) |
| `--discussions` | Add a Discussions contact link, URL taken from `git origin` |
| `--dry-run` | Print a unified diff and write nothing |
| `--verbose` | Print the full generated files |
| `--self-check` | Run a built-in correctness test |
| `--report` | Open a pre-filled email to report an issue |

## What you get

| File | Purpose |
|------|---------|
| `.github/ISSUE_TEMPLATE/config.yml` | `blank_issues_enabled: false` plus contact links, ordered docs → upstream → Discussions |
| `.github/ISSUE_TEMPLATE/bug.yml` | Repro steps, expected behaviour and environment are `required: true` |
| `.github/ISSUE_TEMPLATE/feature.yml` | Problem before solution, alternatives optional |
| `.github/ISSUE_TEMPLATE/question.yml` | Only when there is no Discussions link, so nothing is left unrouted |

**It never overwrites.** An existing file is reported and left alone; merge by hand.

Two manual steps GitHub does not do for you: **create the labels** (`needs-triage`, `bug`, `enhancement`, `question` — a form cannot add a label that does not exist) and open `/issues/new/choose` to confirm the chooser renders.

## Why `required: true` and not a bot

GitHub enforces a required form field at submit time, before the issue exists. A triage bot has to run afterwards, costs money per issue, and is exactly the "hostile gate" maintainers complain about — a comment bot telling someone their issue is invalid. The form just asks once, politely, and GitHub does the rest.

## Support the Project

Issue Gate is free and open source. Like it?

- [Buy the DevTools Bundle](https://danyblitz.gumroad.com/l/zjkam) — standalone .exe + 2 extra tools + guide, pay what you want
- [Buy me a coffee](https://danyblitz.gumroad.com/l/hrvpiu) — one-time support

## Report a bug

Found a bug or something weird? Run:

```bash
python -m tools.issue-gate --report
```

This opens a pre-filled email. Send it and I'll get notified automatically.

You can also email **danyblitz@googlemail.com** directly. Use the subject format:

```
[TOOL-REPORT] issue-gate <what happened>
```

## License

MIT
