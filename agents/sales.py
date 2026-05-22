"""Sales department agents: MonetizationWorker, SalesDirector."""

from __future__ import annotations

from .base import BaseAgent
from config import MODEL_WORKER, MODEL_DIRECTOR


# ---------------------------------------------------------------------------
# Worker: Monetization
# ---------------------------------------------------------------------------

class MonetizationWorker(BaseAgent):
    """Identifies affiliate programs and ad placement strategies."""

    def __init__(self) -> None:
        super().__init__(
            name="Monetization Specialist",
            role="Affiliate & Ad Monetization Expert",
            system_prompt=(
                "You are a monetization expert specializing in affiliate marketing and ad revenue "
                "for content businesses. Your job is to identify the best ways to monetize "
                "specific content pieces. "
                "For each content piece, you provide: "
                "1. AFFILIATE PROGRAMS: Top 3-5 relevant affiliate programs with "
                "   estimated commission rates and cookie duration "
                "2. PRODUCT RECOMMENDATIONS: Specific products/services to recommend naturally "
                "   within the content "
                "3. AD PLACEMENT STRATEGY: Optimal ad placement (above fold, in-content, "
                "   sidebar) for maximum RPM without hurting UX "
                "4. REVENUE PROJECTIONS: Conservative monthly revenue estimate if the article "
                "   ranks top-3 for its target keyword (based on typical traffic and conversion) "
                "5. ADDITIONAL MONETIZATION: Sponsored content opportunities, lead gen, "
                "   digital products, or email list building angles "
                "Be specific with program names (Amazon Associates, ShareASale, Commission "
                "Junction, Impact, etc.) and realistic with projections."
            ),
            model=MODEL_WORKER,
        )


# ---------------------------------------------------------------------------
# Director: Sales Director
# ---------------------------------------------------------------------------

_SALES_TOOLS = [
    {
        "name": "plan_monetization",
        "description": (
            "Develop a monetization strategy for a content piece. "
            "Returns affiliate program recommendations, ad placement strategy, "
            "and revenue projections."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content to monetize: topic, target audience, "
                        "primary keywords, and content type."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Traffic estimates, niche information, or competitive context.",
                },
            },
            "required": ["task"],
        },
    },
]


class SalesDirector(BaseAgent):
    """Manages monetization strategy and revenue optimization."""

    def __init__(self) -> None:
        super().__init__(
            name="Sales Director",
            role="Sales & Monetization Department Director",
            system_prompt=(
                "You are the Sales Director at Lumen Industries, a content-based business. "
                "Your department is responsible for maximizing revenue from content through "
                "affiliate marketing, advertising, sponsored content, and other monetization "
                "channels. "
                "When given a content monetization task: "
                "1. Use 'plan_monetization' to develop a comprehensive revenue strategy "
                "Compile the results into a monetization playbook that includes: "
                "- Recommended affiliate programs with sign-up links and commission structures "
                "- Strategic ad placement recommendations "
                "- Revenue projections (conservative and optimistic scenarios) "
                "- Action items for implementation priority "
                "Focus on realistic, achievable revenue streams that align with the content."
            ),
            model=MODEL_DIRECTOR,
        )
        self._monetization_worker = MonetizationWorker()

    def run_monetization(self, task: str) -> str:
        """Run the monetization planning pipeline."""
        return self.run(task=task, tools=_SALES_TOOLS)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        task = tool_input.get("task", "")
        context = tool_input.get("context", "")

        if tool_name == "plan_monetization":
            prompt = task
            if context:
                prompt = f"{task}\n\nContext:\n{context}"
            return self._monetization_worker.run(
                f"Develop a complete monetization strategy for this content:\n\n{prompt}"
            )
        else:
            return f"Unknown tool: {tool_name}"
