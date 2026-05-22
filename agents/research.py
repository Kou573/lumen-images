"""Research department agents: TrendAnalyzerWorker, KeywordResearchWorker, ResearchDirector."""

from __future__ import annotations

from .base import BaseAgent
from config import MODEL_WORKER, MODEL_DIRECTOR


# ---------------------------------------------------------------------------
# Worker: Trend Analyzer
# ---------------------------------------------------------------------------

class TrendAnalyzerWorker(BaseAgent):
    """Analyzes trending topics for content opportunities."""

    def __init__(self) -> None:
        super().__init__(
            name="Trend Analyzer",
            role="Trend Analysis Specialist",
            system_prompt=(
                "You are an expert at finding trending topics and viral content opportunities. "
                "Your job is to identify what's popular right now in the given niche, "
                "what people are searching for, and what types of content are getting the most "
                "engagement. Focus on practical, actionable trends that a content creator can "
                "leverage today. Provide specific topic ideas, explain WHY they are trending, "
                "and rate each trend by its monetization potential (1-10). "
                "Be concise but thorough."
            ),
            model=MODEL_WORKER,
        )


# ---------------------------------------------------------------------------
# Worker: Keyword Research
# ---------------------------------------------------------------------------

class KeywordResearchWorker(BaseAgent):
    """Finds profitable keywords for SEO."""

    def __init__(self) -> None:
        super().__init__(
            name="Keyword Researcher",
            role="SEO Keyword Research Expert",
            system_prompt=(
                "You are an SEO keyword research expert. Your job is to identify profitable, "
                "high-intent keywords for blog posts and affiliate content. "
                "For each keyword, provide: the keyword phrase, estimated monthly search volume "
                "(low/medium/high), keyword difficulty (easy/medium/hard), commercial intent "
                "(informational/commercial/transactional), and suggested content angle. "
                "Prioritize long-tail keywords with commercial or transactional intent that "
                "have lower competition. Group related keywords into clusters."
            ),
            model=MODEL_WORKER,
        )


# ---------------------------------------------------------------------------
# Director: Research Director
# ---------------------------------------------------------------------------

_RESEARCH_TOOLS = [
    {
        "name": "analyze_trends",
        "description": (
            "Analyze trending topics and viral content opportunities in a niche. "
            "Returns a list of trending topics with monetization potential ratings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The niche or topic area to analyze for trends.",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the target audience or goals.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "research_keywords",
        "description": (
            "Research profitable SEO keywords for a given topic or niche. "
            "Returns keyword clusters with volume, difficulty, and intent data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The topic or niche to research keywords for.",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context such as target audience or content type.",
                },
            },
            "required": ["task"],
        },
    },
]


class ResearchDirector(BaseAgent):
    """Coordinates research workers to gather market intelligence."""

    def __init__(self) -> None:
        super().__init__(
            name="Research Director",
            role="Research Department Director",
            system_prompt=(
                "You are the Research Director at Lumen Industries, a content-based business. "
                "Your department is responsible for identifying market opportunities through "
                "trend analysis and keyword research. "
                "When given a research task, you coordinate your team of specialists: "
                "- Use 'analyze_trends' to discover what's trending and why "
                "- Use 'research_keywords' to find profitable SEO keywords "
                "Synthesize both outputs into a comprehensive research report that gives the "
                "Content Department everything they need to create high-performing content. "
                "Always use both tools for a complete picture."
            ),
            model=MODEL_DIRECTOR,
        )
        self._trend_worker = TrendAnalyzerWorker()
        self._keyword_worker = KeywordResearchWorker()

    def run_research(self, task: str) -> str:
        """Run a full research cycle on the given task."""
        return self.run(task=task, tools=_RESEARCH_TOOLS)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        task = tool_input.get("task", "")
        context = tool_input.get("context", "")
        prompt = task if not context else f"{task}\n\nContext: {context}"

        if tool_name == "analyze_trends":
            return self._trend_worker.run(
                f"Analyze trending topics for the following niche/topic:\n\n{prompt}"
            )
        elif tool_name == "research_keywords":
            return self._keyword_worker.run(
                f"Research profitable SEO keywords for:\n\n{prompt}"
            )
        else:
            return f"Unknown tool: {tool_name}"
