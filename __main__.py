"""Issue Gate — generate GitHub issue forms that require a real reproduction.

GitHub already ships the gate: YAML issue forms plus a chooser config that can
hide the blank-issue bypass. The default GitHub bug form leaves "Steps To
Reproduce" as required: false, so "doesn't work" reports still land on the
maintainer. This tool emits the same native files with the fields that cost
maintainer time marked required, plus contact links ordered by usefulness.
No dependencies, no API, no AI.
"""
import difflib
import re
import sys
import argparse
from pathlib import Path

TEMPLATE_DIR = Path(".github") / "ISSUE_TEMPLATE"

# (marker files that mean "this ecosystem", environment field to prefill)
STACKS = (
    (("package.json",), "Node"),
    (("pyproject.toml", "requirements.txt", "setup.py"), "Python"),
    (("Cargo.toml",), "Rust"),
    (("go.mod",), "Go"),
    (("pom.xml", "build.gradle", "build.gradle.kts"), "JVM"),
    (("Gemfile",), "Ruby"),
    (("composer.json",), "PHP"),
)

LABELS = "needs-triage"


def label_hint() -> str:
    return ", ".join([LABELS, "bug", "enhancement", "question"])


def detect_env(repo: Path) -> list[str]:
    fields = ["OS"]
    for markers, label in STACKS:
        if any((repo / marker).exists() for marker in markers):
            fields.append(label)
    return fields


def git_origin(repo: Path) -> str:
    """Best-effort https GitHub URL for the repo, from .git/config (no subprocess)."""
    config = repo / ".git" / "config"
    if not config.exists():
        return ""
    match = re.search(r"url\s*=\s*(\S+)", config.read_text(encoding="utf-8", errors="ignore"))
    if not match:
        return ""
    url = match.group(1).strip()
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    url = re.sub(r"\.git$", "", url)
    return url if url.startswith("https://github.com/") else ""


def bug_form(env: list[str]) -> str:
    value = "".join(f"          - {field}:\n" for field in env)
    return f"""name: Bug report
description: Something is broken and I can show you how to reproduce it
title: "[BUG] "
labels: ["bug", "{LABELS}"]
body:
  - type: checkboxes
    attributes:
      label: Before you open this
      options:
        - label: I searched the existing issues for this problem
          required: true
        - label: This is not a security report
          required: true
  - type: textarea
    attributes:
      label: What happened?
      description: The behaviour you got, with the error or wrong output quoted.
    validations:
      required: true
  - type: textarea
    attributes:
      label: Steps to reproduce
      description: Numbered steps, starting from a fresh checkout.
      placeholder: |
        1. Install with ...
        2. Run ...
        3. See error ...
    validations:
      required: true
  - type: textarea
    attributes:
      label: What did you expect?
    validations:
      required: true
  - type: textarea
    attributes:
      label: Environment
      render: markdown
      value: |
{value}    validations:
      required: true
  - type: textarea
    attributes:
      label: Logs or traceback
      description: Optional. Drag files straight into this box.
      render: text
    validations:
      required: false
"""


def feature_form() -> str:
    return f"""name: Feature request
description: Propose a change, starting from the problem it solves
title: "[FEATURE] "
labels: ["enhancement", "{LABELS}"]
body:
  - type: checkboxes
    attributes:
      label: Before you open this
      options:
        - label: I searched the existing issues for this idea
          required: true
  - type: textarea
    attributes:
      label: The problem
      description: What you cannot do today, and who it affects.
    validations:
      required: true
  - type: textarea
    attributes:
      label: Proposed change
      description: The smallest change that would fix it.
    validations:
      required: true
  - type: textarea
    attributes:
      label: Alternatives you considered
      description: Optional. Workarounds or designs you ruled out, and why.
    validations:
      required: false
"""


def question_form() -> str:
    return f"""name: Question
description: Usage help or "how do I..."
labels: ["question", "{LABELS}"]
body:
  - type: checkboxes
    attributes:
      label: Before you open this
      options:
        - label: I searched the existing issues and the documentation
          required: true
  - type: input
    attributes:
      label: Short question
    validations:
      required: true
  - type: textarea
    attributes:
      label: What I tried
    validations:
      required: true
  - type: textarea
    attributes:
      label: Config or code
      description: Optional. The smallest snippet that shows the problem.
      render: text
    validations:
      required: false
"""


def chooser_config(docs: str, upstream: str, discussions: str) -> str:
    links = []
    if docs:
        links.append(f"  - name: Documentation\n    url: {docs}\n    about: Read this first, it answers most questions.\n")
    if upstream:
        links.append(
            f"  - name: Upstream project\n    url: {upstream}\n    about: This project wraps another one, check upstream docs first.\n"
        )
    if discussions:
        links.append(
            f"  - name: GitHub Discussions\n    url: {discussions}\n    about: Ask and answer questions here instead of opening an issue.\n"
        )
    body = "".join(links)
    return f"""# Generated by issue-gate. Order matters: the first useful link wins.
blank_issues_enabled: false
contact_links:
{body}"""


def build_files(repo: Path, docs: str, upstream: str, discussions_flag: bool) -> dict[str, str]:
    files = {"bug.yml": bug_form(detect_env(repo)), "feature.yml": feature_form()}
    discussions = ""
    if discussions_flag:
        origin = git_origin(repo)
        if origin:
            discussions = f"{origin}/discussions"
        else:
            print("  [WARN] no GitHub origin found, skipping the Discussions link (add it by hand).")
    config = chooser_config(docs, upstream, discussions)
    if not discussions:
        files["question.yml"] = question_form()
    files["config.yml"] = config
    return files


def apply_files(repo: Path, files: dict[str, str], dry_run: bool) -> tuple[list[str], list[str]]:
    written, skipped = [], []
    for name, content in sorted(files.items()):
        target = repo / TEMPLATE_DIR / name
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        if before:
            skipped.append(name)
            continue
        if dry_run:
            written.append(name)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(name)
    return written, skipped


def show_diff(repo: Path, files: dict[str, str]) -> None:
    for name, content in sorted(files.items()):
        target = repo / TEMPLATE_DIR / name
        before = target.read_text(encoding="utf-8") if target.exists() else ""
        if before == content:
            continue
        target_rel = "/".join(TEMPLATE_DIR.parts + (name,))  # posix: a pasted diff must apply in a PR
        diff = difflib.unified_diff(
            before.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{target_rel}" if before else "/dev/null",
            tofile=f"b/{target_rel}",
        )
        sys.stdout.writelines(diff)


def self_check() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "package.json").write_text("{}", encoding="utf-8")
        (repo / ".github").mkdir()

        files = build_files(repo, docs="", upstream="", discussions_flag=False)
        assert label_hint() == "needs-triage, bug, enhancement, question", f"label hint mangled: {label_hint()}"
        assert "blank_issues_enabled: false" in files["config.yml"], "blank issues are not disabled"
        assert "config.yml" in files and files["config.yml"].endswith("contact_links:\n"), "empty chooser config"
        assert files["bug.yml"].count("required: true") >= 5, "bug form does not gate on repro"
        assert "          - Node:\n" in files["bug.yml"], "ecosystem field missing for a Node repo"
        assert "          - Python:\n" not in files["bug.yml"], "phantom field for an absent ecosystem"
        assert "question.yml" in files, "no fallback form and no Discussions link"
        assert "title: \"[BUG] \"" in files["bug.yml"], "title prefix missing"

        pyrepo = Path(tmp) / "py"
        (pyrepo / ".git").mkdir(parents=True)
        (pyrepo / "pyproject.toml").write_text("", encoding="utf-8")
        (pyrepo / ".git" / "config").write_text(
            '[remote "origin"]\n\turl = git@github.com:acme/lib.git\n', encoding="utf-8"
        )
        pyfiles = build_files(pyrepo, docs="https://example.com/docs", upstream="https://example.com/up", discussions_flag=True)
        assert "          - Python:\n" in pyfiles["bug.yml"], "Python field missing"
        assert "question.yml" not in pyfiles, "redundant question form with a Discussions link"
        assert "url: https://github.com/acme/lib/discussions" in pyfiles["config.yml"], "discussions URL not derived from origin"
        assert "blank issues" not in pyfiles["config.yml"], "comment leaked into the chooser"
        assert pyfiles["config.yml"].index("Documentation") < pyfiles["config.yml"].index("Upstream"), "links out of order"
        assert pyfiles["config.yml"].index("Upstream") < pyfiles["config.yml"].index("Discussions"), "links out of order"

        # No clobber: an existing file is never overwritten.
        existing = repo / TEMPLATE_DIR / "bug.yml"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("name: mine\n", encoding="utf-8")
        written, skipped = apply_files(repo, files, dry_run=False)
        assert "bug.yml" in skipped, "existing bug.yml was not skipped"
        assert existing.read_text(encoding="utf-8") == "name: mine\n", "existing file was clobbered"
        assert set(written) == {"config.yml", "feature.yml", "question.yml"}, f"unexpected writes: {written}"

        # Dry run leaves the disk alone.
        before = sorted(p.name for p in (repo / TEMPLATE_DIR).iterdir())
        apply_files(repo, files, dry_run=True)
        assert sorted(p.name for p in (repo / TEMPLATE_DIR).iterdir()) == before, "dry run wrote to disk"

        try:
            import yaml
        except ImportError:
            print("self-check OK: forms generated, gate required, existing files kept (PyYAML absent, parse not verified)")
        else:
            for name, content in files.items():
                assert isinstance(yaml.safe_load(content), dict), f"{name} is not valid YAML"
            print("self-check OK: forms generated, gate required, existing files kept, YAML parses")
    return 0


def report_to_email(message: str):
    import webbrowser
    from urllib.parse import quote

    subject = "[TOOL-REPORT] issue-gate bug or issue"
    webbrowser.open(f"mailto:danyblitz@googlemail.com?subject={quote(subject)}&body={quote(message)}")


def main():
    parser = argparse.ArgumentParser(
        prog="issue-gate",
        description="Generate GitHub issue forms and a chooser config that require a real reproduction.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="Path to the repository (default: current directory)")
    parser.add_argument("--docs", default="", metavar="URL", help="Documentation URL for a chooser contact link")
    parser.add_argument("--upstream", default="", metavar="URL", help="Upstream project URL for a chooser contact link")
    parser.add_argument("--discussions", action="store_true", help="Route questions to GitHub Discussions (URL from git origin)")
    parser.add_argument("--dry-run", action="store_true", help="Print the diff and write nothing")
    parser.add_argument("--verbose", action="store_true", help="Print the full generated files")
    parser.add_argument("--self-check", action="store_true", help="Run internal correctness check")
    parser.add_argument("--report", action="store_true", help="Open a pre-filled email to report an issue")
    args = parser.parse_args()

    if args.self_check:
        sys.exit(self_check())

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists() and not (repo / TEMPLATE_DIR).exists():
        parser.error(f"{repo} does not look like a repository (no .git and no {TEMPLATE_DIR})")

    files = build_files(repo, args.docs, args.upstream, args.discussions)
    written, skipped = apply_files(repo, files, args.dry_run)

    print(f"\n=== {repo.name} ===")
    if args.verbose or args.dry_run:
        show_diff(repo, files)
        print()
    for name in written:
        print(f"  {'would write' if args.dry_run else 'wrote'} {TEMPLATE_DIR / name}")
    for name in skipped:
        print(f"  [SKIP] {TEMPLATE_DIR / name}: already exists, left untouched")
    if not written:
        print("  Nothing to do.")

    env = detect_env(repo)
    print("\n  Environment fields prefilled: " + ", ".join(env))
    print("  Create these labels or the forms will open without them: " + label_hint())
    if "Discussions" not in files["config.yml"]:
        print("  No Discussions link: a Question form was added so nothing is left unrouted.")
    print("  Test it: open /issues/new/choose on the repo after pushing.")

    if args.report:
        report_to_email(f"repo: {repo}\nwritten: {written}\nskipped: {skipped}\nenv: {env}")
        print("\n  Email draft opened — send it and I'll get notified automatically.")


if __name__ == "__main__":
    main()
