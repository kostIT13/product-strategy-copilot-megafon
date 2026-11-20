"""Build a local copy of the training case without recording a human choice."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_assessment_service import (
    SourceAssessmentService,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.ledger import add_claim, add_gap, add_option
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source, fetch_web_source


ASSETS = Path(__file__).resolve().parent
BRIEF = ASSETS.parents[1] / "specs/Пример брифа.pdf"
BRIEF_SHA256 = "558d2c665caa4f4954135c8bbfb69d791e398dcdc5b625d5ded7bdb2d0eb0fa5"
SITE_URL = "https://support.google.com/pixelphone/answer/2819524/?hl=en"
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


def paragraph_locator(case, source, quote):
    text = (case / source["extracted_text_path"]).read_text(encoding="utf-8")
    paragraphs = (line for line in text.splitlines() if line.strip())
    matches = [i for i, paragraph in enumerate(paragraphs, 1) if quote in paragraph]
    if len(matches) != 1:
        raise ValueError(f"Expected one citation match in {source['title']}: {quote}")
    return f"paragraph:{matches[0]}"


def build(project_id: str, projects_dir: Path, *, fetch_site: bool = False) -> Path:
    try:
        import pypdf  # noqa: F401
    except ImportError as exc:
        raise ValueError(
            "Install the documents extra before building this case."
        ) from exc

    brief = BRIEF.read_bytes()
    if hashlib.sha256(brief).hexdigest() != BRIEF_SHA256:
        raise ValueError("The bundled training brief does not match the expected PDF.")
    evidence = json.loads((ASSETS / "evidence.json").read_text(encoding="utf-8"))
    documents = {name: (ASSETS / name).read_bytes() for name in CASE_DOCUMENTS}
    baseline = (ASSETS / "materials/baseline.csv").read_bytes()
    excerpt = (ASSETS / "materials/pixel-help-excerpt.html").read_bytes()

    projects_dir = projects_dir.resolve()
    case = init_project(project_id, projects_dir)
    with case_access(projects_dir, project_id):
        pdf = case / "materials/sample-brief.pdf"
        pdf.parent.mkdir()
        pdf.write_bytes(brief)
        table = pdf.parent / "baseline.csv"
        table.write_bytes(baseline)
        if fetch_site:
            site = fetch_web_source(case, SITE_URL, title="Google Pixel Phone Help")
        else:
            snapshot = pdf.parent / "pixel-help-excerpt.html"
            snapshot.write_bytes(excerpt)
            site = add_local_source(
                case, snapshot, title="Google Pixel Phone Help — офлайн-выдержка"
            )
        sources = {
            "brief": add_local_source(
                case, pdf, title="Пример брифа учебного оператора"
            ),
            "table": add_local_source(
                case, table, title="Учебная таблица исходных показателей"
            ),
            "site": site,
        }
        assessments = SourceAssessmentService(FileWorkflowStore(projects_dir))
        for role, source in sources.items():
            source_id = source["source_id"]
            inspected = assessments.inspect(project_id, source_id)
            assessments.record(
                project_id,
                {
                    "operation_id": uuid4(),
                    "source_id": source_id,
                    "expected_workflow_version": inspected["workflow_version"],
                    "expected_content_hash": inspected["content_hash"],
                    "expected_source_record_hash": inspected["source_record_hash"],
                    "assessed_by": "Codex — подготовка учебного примера",
                    **evidence["source_assessments"][role],
                },
            )
        for row in evidence["claims"]:
            source = sources[row.get("source", "brief")]
            locator = row.get("locator") or paragraph_locator(
                case, source, row["quote"]
            )
            add_claim(
                case,
                row["text"],
                row.get("type", "synthetic"),
                [source["source_id"]],
                [locator],
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
    parser.add_argument(
        "--fetch-site",
        action="store_true",
        help="Fetch the public Google help page over HTTPS.",
    )
    args = parser.parse_args()
    print(build(args.project_id, args.projects_dir, fetch_site=args.fetch_site))


if __name__ == "__main__":
    main()
