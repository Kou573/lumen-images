"""Marketing department agents: SocialMediaWorker, MarketingDirector."""

from __future__ import annotations

from .base import BaseAgent
from config import MODEL_WORKER, MODEL_DIRECTOR


# ---------------------------------------------------------------------------
# Worker: Social Media
# ---------------------------------------------------------------------------

class SocialMediaWorker(BaseAgent):
    """Creates social media posts for content distribution."""

    def __init__(self) -> None:
        super().__init__(
            name="Social Media Specialist",
            role="Social Media Content Creator",
            system_prompt=(
                "You are a social media expert who creates platform-optimized posts to "
                "distribute blog content and drive traffic. "
                "For each piece of content, you create posts tailored to multiple platforms: "
                "- Twitter/X: Punchy, 280-char max, 1-2 hashtags, strong hook "
                "- LinkedIn: Professional tone, 150-300 words, value-focused, 3-5 hashtags "
                "- Facebook: Conversational, 100-200 words, question or story-driven "
                "- Instagram: Visual-first caption, 150-200 words, 10-15 relevant hashtags "
                "- Pinterest: Keyword-rich description, 200-300 words "
                "Focus on driving clicks back to the article. Include a clear CTA on each post. "
                "Format each platform's post clearly with the platform name as a header."
            ),
            model=MODEL_WORKER,
        )


# ---------------------------------------------------------------------------
# Director: Marketing Director
# ---------------------------------------------------------------------------

_MARKETING_TOOLS = [
    {
        "name": "create_social_posts",
        "description": (
            "Create platform-optimized social media posts to distribute content and drive traffic. "
            "Returns a full social media post package for Twitter, LinkedIn, Facebook, "
            "Instagram, and Pinterest."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "The content to promote: article title, main topics, key value props, "
                        "and target audience."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": "Article URL (placeholder), key stats, or quotes to highlight.",
                },
            },
            "required": ["task"],
        },
    },
]


class MarketingDirector(BaseAgent):
    """Plans content distribution and marketing campaigns."""

    def __init__(self) -> None:
        super().__init__(
            name="Marketing Director",
            role="Marketing Department Director",
            system_prompt=(
                "You are the Marketing Director at Lumen Industries, a content-based business. "
                "Your department is responsible for distributing content and driving traffic "
                "to generate revenue. "
                "When given content to promote: "
                "1. Use 'create_social_posts' to generate platform-specific social media content "
                "   that will drive traffic to the article "
                "Create a distribution strategy that includes: "
                "- Social media posts for all major platforms "
                "- Recommended posting schedule (days/times) "
                "- Suggested paid promotion budget allocation if applicable "
                "- Email newsletter snippet for subscribers "
                "Focus on maximizing organic reach and traffic."
            ),
            model=MODEL_DIRECTOR,
        )
        self._social_worker = SocialMediaWorker()

    def run_distribution(self, task: str) -> str:
        """Run the marketing distribution pipeline."""
        return self.run(task=task, tools=_MARKETING_TOOLS)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        task = tool_input.get("task", "")
        context = tool_input.get("context", "")

        if tool_name == "create_social_posts":
            prompt = task
            if context:
                prompt = f"{task}\n\nAdditional Details:\n{context}"
            return self._social_worker.run(
                f"Create social media posts to promote this content:\n\n{prompt}"
            )
        else:
            return f"Unknown tool: {tool_name}"
