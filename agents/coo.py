"""COO agent — main orchestrator for Lumen Industries."""

from __future__ import annotations

import datetime
from pathlib import Path

from .base import BaseAgent
from .research import ResearchDirector
from .content import ContentDirector
from .marketing import MarketingDirector
from .sales import SalesDirector
from config import MODEL_EXECUTIVE, OUTPUT_DIR


# ---------------------------------------------------------------------------
# Tool schemas for the four departments the COO can call
# ---------------------------------------------------------------------------

_COO_TOOLS = [
    {
        "name": "call_research_department",
        "description": (
            "Delegate a research task to the Research Department. "
            "They will analyze trends and research profitable SEO keywords. "
            "Returns a comprehensive research report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The research objective: niche, topic, or specific question.",
                },
                "context": {
                    "type": "string",
                    "description": "CEO goal or broader context for the research.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_content_department",
        "description": (
            "Delegate a content creation task to the Content Department. "
            "They will write and SEO-optimize articles, blog posts, or affiliate content. "
            "Returns a full content package with the article and SEO metadata."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content brief: topic, content type, target audience, "
                        "key angle, and any specific requirements."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Research data and keywords from the Research Department.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_marketing_department",
        "description": (
            "Delegate a distribution task to the Marketing Department. "
            "They will create social media posts for all major platforms to drive traffic. "
            "Returns a full social media distribution package with posting schedule."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content to promote: article title, summary, main topics, "
                        "and target audience."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Article URL placeholder, key stats, or quotes to highlight.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "call_sales_department",
        "description": (
            "Delegate a monetization task to the Sales Department. "
            "They will identify affiliate programs, ad placements, and revenue strategies. "
            "Returns a monetization playbook with revenue projections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content to monetize: topic, niche, target audience, "
                        "and primary keywords."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Traffic estimates, niche details, or competitive context.",
                },
            },
            "required": ["task"],
        },
    },
]


# ---------------------------------------------------------------------------
# COO Agent
# ---------------------------------------------------------------------------

class COO(BaseAgent):
    """
    Chief Operations Officer — orchestrates all departments to achieve the CEO's goals.

    Uses claude-opus-4-7 with adaptive thinking for complex orchestration.
    Each department is exposed as a tool the COO can call.
    Final results are saved to the output/ directory.
    """

    def __init__(self) -> None:
        super().__init__(
            name="COO",
            role="Chief Operations Officer",
            system_prompt=(
                "You are the Chief Operations Officer (COO) of Lumen Industries, "
                "a content-based business focused on generating revenue through "
                "SEO blog posts, affiliate content, and digital marketing. "
                "\n\n"
                "Your CEO gives you high-level goals. Your job is to orchestrate the "
                "four departments at your disposal to turn those goals into real, "
                "deliverable content assets:\n"
                "1. Research Department — trend analysis + keyword research\n"
                "2. Content Department — article writing + SEO optimization\n"
                "3. Marketing Department — social media distribution strategy\n"
                "4. Sales Department — monetization strategy + revenue projections\n"
                "\n"
                "WORKFLOW:\n"
                "- Always start with Research to understand the market and find keywords\n"
                "- Pass research output to Content as full context\n"
                "- Pass the written content summary to Marketing for distribution\n"
                "- Pass content topic + keyword data to Sales for monetization\n"
                "\n"
                "After all departments have delivered, compile a CEO Report that includes:\n"
                "- Executive Summary (2-3 sentences)\n"
                "- Key Deliverables (what was produced)\n"
                "- Revenue Opportunity (from Sales report)\n"
                "- Next Steps\n"
                "\n"
                "Be decisive, efficient, and results-oriented. "
                "Call departments in a logical sequence to build on each other's work."
            ),
            model=MODEL_EXECUTIVE,
            use_thinking=True,
        )
        # Department directors are lazily instantiated on first tool call
        self._research_director: ResearchDirector | None = None
        self._content_director: ContentDirector | None = None
        self._marketing_director: MarketingDirector | None = None
        self._sales_director: SalesDirector | None = None

        # Accumulate department outputs for final file save
        self._department_outputs: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute_ceo_goal(self, goal: str) -> str:
        """Execute a CEO goal by orchestrating all departments."""
        result = self.run(task=goal, tools=_COO_TOOLS)
        self._save_outputs(goal, result)
        return result

    # ------------------------------------------------------------------
    # Tool dispatcher
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        task = tool_input.get("task", "")
        context = tool_input.get("context", "")
        combined = f"{task}\n\nContext:\n{context}" if context else task

        if tool_name == "call_research_department":
            if self._research_director is None:
                self._research_director = ResearchDirector()
            result = self._research_director.run_research(combined)
            self._department_outputs["research"] = result
            return result

        elif tool_name == "call_content_department":
            if self._content_director is None:
                self._content_director = ContentDirector()
            result = self._content_director.run_content_pipeline(combined)
            self._department_outputs["content"] = result
            return result

        elif tool_name == "call_marketing_department":
            if self._marketing_director is None:
                self._marketing_director = MarketingDirector()
            result = self._marketing_director.run_distribution(combined)
            self._department_outputs["marketing"] = result
            return result

        elif tool_name == "call_sales_department":
            if self._sales_director is None:
                self._sales_director = SalesDirector()
            result = self._sales_director.run_monetization(combined)
            self._department_outputs["sales"] = result
            return result

        else:
            return f"Unknown department tool: {tool_name}"

    # ------------------------------------------------------------------
    # Output persistence
    # ------------------------------------------------------------------

    def _save_outputs(self, goal: str, coo_report: str) -> None:
        """Save all department outputs and the final COO report to output/."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path: Path = OUTPUT_DIR / f"run_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)

        # Save individual department reports
        for dept, content in self._department_outputs.items():
            dept_file = output_path / f"{dept}_report.md"
            dept_file.write_text(content, encoding="utf-8")

        # Save the final COO executive report
        report_file = output_path / "coo_executive_report.md"
        report_content = (
            f"# Lumen Industries — COO Executive Report\n\n"
            f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**CEO Goal:** {goal}\n\n"
            f"---\n\n"
            f"{coo_report}\n"
        )
        report_file.write_text(report_content, encoding="utf-8")

        # Save a combined deliverables file
        combined_file = output_path / "all_deliverables.md"
        sections = [
            f"# Lumen Industries — Full Deliverables\n\n"
            f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**CEO Goal:** {goal}\n\n"
        ]
        dept_titles = {
            "research": "## Research Report",
            "content": "## Content Package",
            "marketing": "## Marketing Distribution Plan",
            "sales": "## Monetization Playbook",
        }
        for dept, title in dept_titles.items():
            if dept in self._department_outputs:
                sections.append(f"{title}\n\n{self._department_outputs[dept]}\n\n---\n\n")
        sections.append(f"## COO Executive Report\n\n{coo_report}\n")
        combined_file.write_text("".join(sections), encoding="utf-8")

        self._last_output_path = output_path
