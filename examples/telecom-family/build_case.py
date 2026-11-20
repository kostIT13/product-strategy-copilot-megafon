"""Build a local copy of the training case without recording a human choice."""

import argparse
import hashlib
import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.cli import init_project
from product_strategy_agent.ledger import add_claim, add_gap, add_option
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source


ASSETS = Path(__file__).resolve().parent
BRIEF = ASSETS.parents[1] / "specs/Пример брифа.pdf"
BRIEF_SHA256 = "558d2c665caa4f4954135c8bbfb69d791e398dcdc5b625d5ded7bdb2d0eb0fa5"
CASE_DOCUMENTS = (
    "01_brief.md",
    "02_research-plan.md",
    "analysis/forecast.py",
    "analysis/options-comparison.md",
    "analysis/strategy-five-parts.md",
    "drafts/communication-strategy.md",
    "drafts/product-strategy.md",
    "drafts/validation-plan.md",
)


def build(project_id: str, projects_dir: Path) -> Path:
    try:
        import pypdf  # noqa: F401
    except ImportError as exc:
        raise ValueError("Install the documents extra before building this case.") from exc

    brief = BRIEF.read_bytes()
    if hashlib.sha256(brief).hexdigest() != BRIEF_SHA256:
        raise ValueError("The bundled training brief does not match the expected PDF.")
    evidence = json.loads((ASSETS / "evidence.json").read_text(encoding="utf-8"))
    documents = {name: (ASSETS / name).read_bytes() for name in CASE_DOCUMENTS}

    projects_dir = projects_dir.resolve()
    case = init_project(project_id, projects_dir)
    with case_access(projects_dir, project_id):
        pdf = case / "materials/sample-brief.pdf"
        pdf.parent.mkdir()
        pdf.write_bytes(brief)
        source = add_local_source(case, pdf, title="Пример брифа учебного оператора")
        for row in evidence["claims"]:
            add_claim(
                case,
                row["text"],
                "synthetic",
                [source["source_id"]],
                [row["locator"]],
                [row["quote"]],
            )
        for row in evidence["gaps"]:
            add_gap(case, **row)
        for row in evidence["options"]:
            add_option(case, **row)
        for name, contents in documents.items():
            target = case / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
        render_project(case)
    return case


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default="telecom-family-demo")
    parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
    args = parser.parse_args()
    print(build(args.project_id, args.projects_dir))


if __name__ == "__main__":
    main()
