"""Content department agents: WriterWorker, SEOOptimizerWorker, ContentDirector."""

from __future__ import annotations

from .base import BaseAgent
from config import MODEL_WORKER, MODEL_DIRECTOR


# ---------------------------------------------------------------------------
# Worker: Writer
# ---------------------------------------------------------------------------

class WriterWorker(BaseAgent):
    """Writes blog posts, articles, and affiliate content."""

    def __init__(self) -> None:
        super().__init__(
            name="Content Writer",
            role="Expert Content Writer",
            system_prompt=(
                "You are an expert content writer specializing in SEO blogs, affiliate articles, "
                "and monetizable content. You write engaging, informative pieces that rank well "
                "in search engines and convert readers to buyers. "
                "Your writing style is: clear, helpful, and authoritative without being dry. "
                "Structure your articles with: a compelling headline (H1), an intro that hooks "
                "the reader and states the value proposition, well-organized sections with H2/H3 "
                "subheadings, practical information, and a clear conclusion with call-to-action. "
                "Naturally weave in affiliate opportunities and product mentions where relevant. "
                "Target length: 1200-1800 words for standard articles unless specified otherwise. "
                "Include proper markdown formatting."
            ),
            model=MODEL_DIRECTOR,  # Writers need quality output — use sonnet
        )


# ---------------------------------------------------------------------------
# Worker: SEO Optimizer
# ---------------------------------------------------------------------------

class SEOOptimizerWorker(BaseAgent):
    """Optimizes content for search engines."""

    def __init__(self) -> None:
        super().__init__(
            name="SEO Optimizer",
            role="SEO Optimization Expert",
            system_prompt=(
                "You are an SEO optimization expert. Given a piece of content, you improve it "
                "for search engine rankings without sacrificing readability. "
                "Your optimization includes: "
                "1. Meta title (50-60 chars) and meta description (150-160 chars) "
                "2. Primary keyword placement in title, first paragraph, and subheadings "
                "3. LSI/semantic keywords naturally woven throughout "
                "4. Internal linking suggestions (placeholder URLs) "
                "5. Image alt text suggestions "
                "6. Recommended schema markup type "
                "7. Featured snippet optimization (if applicable) "
                "8. On-page SEO score estimate (1-100) with top 3 improvement suggestions. "
                "Return the SEO metadata block and a list of specific optimizations made."
            ),
            model=MODEL_WORKER,
        )


# ---------------------------------------------------------------------------
# Director: Content Director
# ---------------------------------------------------------------------------

_CONTENT_TOOLS = [
    {
        "name": "write_content",
        "description": (
            "Write a high-quality blog post, article, or affiliate content piece. "
            "Returns the full article in markdown format."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content brief: topic, target keywords, tone, angle, "
                        "and any specific requirements."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Research data, keyword insights, or additional context.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "optimize_seo",
        "description": (
            "Optimize a piece of content for SEO. "
            "Returns SEO metadata and a list of optimizations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The content to optimize (full article text).",
                },
                "context": {
                    "type": "string",
                    "description": "Target keywords and additional SEO context.",
                },
            },
            "required": ["task"],
        },
    },
]


class ContentDirector(BaseAgent):
    """Manages the content creation pipeline."""

    def __init__(self) -> None:
        super().__init__(
            name="Content Director",
            role="Content Department Director",
            system_prompt=(
                "You are the Content Director at Lumen Industries, a content-based business. "
                "Your department creates high-quality, SEO-optimized content that generates "
                "revenue through affiliate marketing, ad revenue, and sponsored content. "
                "When given a content task with research data: "
                "1. Use 'write_content' to create the article/post, providing the full research "
                "   context so the writer has everything needed "
                "2. Use 'optimize_seo' to optimize the written content for search engines "
                "Combine both outputs into a final content package: "
                "the full article + SEO metadata block + optimization notes. "
                "Always run both tools in sequence: write first, then optimize."
            ),
            model=MODEL_DIRECTOR,
        )
        self._writer = WriterWorker()
        self._seo_optimizer = SEOOptimizerWorker()
        self._last_written_content: str = ""

    def run_content_pipeline(self, task: str) -> str:
        """Run the full content creation pipeline."""
        return self.run(task=task, tools=_CONTENT_TOOLS)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        task = tool_input.get("task", "")
        context = tool_input.get("context", "")

        if tool_name == "write_content":
            prompt = task
            if context:
                prompt = f"{task}\n\n## Research & Context\n{context}"
            result = self._writer.run(
                f"Write a comprehensive, SEO-optimized article based on this brief:\n\n{prompt}"
            )
            self._last_written_content = result
            return result

        elif tool_name == "optimize_seo":
            content = task
            if not content and self._last_written_content:
                content = self._last_written_content
            ctx_note = f"\n\nTarget Keywords & Context:\n{context}" if context else ""
            return self._seo_optimizer.run(
                f"Optimize this content for SEO:{ctx_note}\n\n---\n{content}"
            )

        else:
            return f"Unknown tool: {tool_name}"
