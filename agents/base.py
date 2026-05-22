"""Base agent class with agentic tool-use loop and streaming."""

from __future__ import annotations

import anthropic

from config import ANTHROPIC_API_KEY


class BaseAgent:
    """Base class for all agents in Lumen Industries."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str,
        use_thinking: bool = False,
    ) -> None:
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.use_thinking = use_thinking
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def run(self, task: str, tools: list | None = None) -> str:
        """
        Run the agentic loop with tool_use support.

        Uses streaming via stream.get_final_message().
        Loops until stop_reason == "end_turn".
        When stop_reason == "tool_use": executes tools and continues.
        Returns final text response.
        """
        messages = [{"role": "user", "content": task}]
        active_tools = tools or []

        # Build system param with prompt caching
        system_param = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        while True:
            # Build kwargs; only COO gets adaptive thinking
            kwargs: dict = {
                "model": self.model,
                "max_tokens": 8192,
                "system": system_param,
                "tools": active_tools,
                "messages": messages,
            }
            if self.use_thinking:
                kwargs["thinking"] = {"type": "adaptive"}

            with self.client.messages.stream(**kwargs) as stream:
                response = stream.get_final_message()

            if response.stop_reason == "end_turn":
                # Extract text from final response
                text_blocks = [
                    block.text
                    for block in response.content
                    if block.type == "text"
                ]
                return "\n".join(text_blocks)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                # Append assistant response (including tool_use blocks)
                messages.append({"role": "assistant", "content": response.content})
                # Append tool results as user turn
                messages.append({"role": "user", "content": tool_results})
                # Continue the loop
                continue

            # Any other stop reason – extract text and return
            text_blocks = [
                block.text for block in response.content if block.type == "text"
            ]
            return "\n".join(text_blocks)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Override in subclasses to handle tool calls."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement _execute_tool "
            f"but received tool call: {tool_name}"
        )
