"""Check tracked Markdown local links/anchors and required repository files."""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from scripts.ci.repository import git

REQUIRED = ("README.md", "pyproject.toml", "uv.lock", ".env.example", "Dockerfile",
            "docker-compose.yml", "alembic.ini", "alembic/env.py",
            ".github/workflows/ci.yml", ".github/workflows/demo.yml",
            ".github/workflows/release.yml", "MANIFEST.in", "docs/distribution.md",
            "knowledge/README.md", "knowledge/catalog.json",
            "AGENTS.md", "agent/README.md", "agent/harness.json", "docs/ide-instructions.md",
            "docs/solution_plans/plan-main.md", "docs/solution_plans/roadmap-full-solution.md",
            "projects/demo/state.json", "projects/table-demo/state.json")
MARKDOWN = MarkdownIt("commonmark")


class ExplicitIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(value for key, value in attrs if key in {"id", "name"} and value)


def parse_document(text):
    tokens = MARKDOWN.parse(text)
    anchors, links, counts = set(), [], Counter()
    html = ExplicitIds()
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            children = tokens[index + 1].children or []
            title = "".join(child.content for child in children if child.type in {"text", "code_inline", "image"})
            slug = re.sub(r"[^\w\- ]", "", title.lower(), flags=re.UNICODE).replace(" ", "-")
            candidate = slug
            while candidate in anchors:
                counts[slug] += 1
                candidate = f"{slug}-{counts[slug]}"
            anchors.add(candidate)
        if token.type == "html_block":
            html.feed(token.content)
        for child in token.children or []:
            if child.type in {"link_open", "image"}:
                links.append(child.attrGet("href" if child.type == "link_open" else "src"))
            if child.type == "html_inline":
                html.feed(child.content)
    return anchors | html.ids, links


def check_docs(root, paths):
    root = root.resolve()
    errors = [f"missing required file: {name}" for name in REQUIRED if not (root / name).is_file()]
    documents = {name: parse_document((root / name).read_text(encoding="utf-8"))
                 for name in paths if name.lower().endswith(".md") and (root / name).is_file()}
    for name, (_, links) in documents.items():
        for link in links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue  # External services are outside this deterministic check.
            target = ((root if url.path.startswith("/") else (root / name).parent) / unquote(url.path).lstrip("/")).resolve() if url.path else (root / name).resolve()
            if not target.is_relative_to(root):
                errors.append(f"{name}: link escapes repository: {link}")
            elif not target.exists():
                errors.append(f"{name}: missing link target: {link}")
            elif url.fragment and target.suffix.lower() == ".md":
                relative = target.relative_to(root).as_posix()
                if relative not in documents:
                    errors.append(f"{name}: Markdown target is not tracked: {link}")
                elif unquote(url.fragment) not in documents[relative][0]:
                    errors.append(f"{name}: missing anchor: {link}")
    return errors, len(documents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors, count = check_docs(args.root, filter(None, git(args.root, "ls-files", "-z")))
    print(json.dumps({"ok": not errors, "documents": count, "errors": errors}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
