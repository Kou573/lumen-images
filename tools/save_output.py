"""Save pipeline output to the output/ directory. No API key required."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path


OUTPUT_DIR = Path(__file__).parent.parent / "output"


def save(goal: str, research: str = "", content: str = "", marketing: str = "", sales: str = "") -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    sections = {
        "research_report.md": research,
        "content_package.md": content,
        "marketing_plan.md": marketing,
        "monetization_playbook.md": sales,
    }
    for filename, body in sections.items():
        if body.strip():
            (run_dir / filename).write_text(body, encoding="utf-8")

    combined = (
        f"# Lumen Industries — Full Deliverables\n\n"
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"**CEO Goal:** {goal}\n\n"
    )
    titles = {
        "research": "## Research Report",
        "content": "## Content Package",
        "marketing": "## Marketing Distribution Plan",
        "sales": "## Monetization Playbook",
    }
    for key, title in titles.items():
        body = locals().get(key, "")
        if body and body.strip():
            combined += f"{title}\n\n{body}\n\n---\n\n"

    (run_dir / "all_deliverables.md").write_text(combined, encoding="utf-8")
    print(f"Saved to: {run_dir}")
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save Lumen Industries pipeline output")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--research", default="")
    parser.add_argument("--content", default="")
    parser.add_argument("--marketing", default="")
    parser.add_argument("--sales", default="")
    args = parser.parse_args()
    save(args.goal, args.research, args.content, args.marketing, args.sales)
