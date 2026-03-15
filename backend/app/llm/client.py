"""LLM client wrapper.

Wraps the OpenAI SDK for structured proposal generation via tool calling.
All model calls in the system go through this module so retry logic, model
selection, token tracking, and error handling are centralized.
"""

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from app.llm.schemas import PROPOSAL_TOOL, ProposalBatch

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.llm_model

    def generate_proposals(self, system_prompt: str, user_prompt: str) -> ProposalBatch:
        """Send a prompt to the LLM and return validated task proposals.

        Args:
            system_prompt: Instructions for how the LLM should generate proposals.
            user_prompt: The assembled context (ingestion data, active tasks, etc.).

        Returns:
            A validated ProposalBatch containing the LLM's proposed task changes.

        Raises:
            LLMError: If the API call fails or the response can't be parsed.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[PROPOSAL_TOOL],
                tool_choice={"type": "function", "function": {"name": "submit_proposals"}},
                temperature=0.2,
            )
        except Exception as e:
            raise LLMError(f"OpenAI API call failed: {e}") from e

        # Extract the tool call from the response
        message = completion.choices[0].message
        if not message.tool_calls:
            raise LLMError(
                "LLM did not return a tool call. "
                f"Response content: {message.content[:200] if message.content else '(empty)'}"
            )

        tool_call = message.tool_calls[0]
        if tool_call.function.name != "submit_proposals":
            raise LLMError(f"Unexpected tool call: {tool_call.function.name}")

        # Parse and validate against Pydantic schema
        try:
            raw_args = tool_call.function.arguments
            # arguments may be a string or already parsed dict depending on provider
            if isinstance(raw_args, str):
                parsed = json.loads(raw_args)
            else:
                parsed = raw_args
            batch = ProposalBatch.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMError(f"Failed to parse tool call arguments: {e}") from e

        logger.info(
            "LLM returned %d proposals (model=%s, tokens=%s)",
            len(batch.proposals),
            completion.model,
            getattr(completion.usage, "total_tokens", "unknown"),
        )

        return batch

    def generate_proposals_with_meta(self, system_prompt: str, user_prompt: str) -> "LLMResult":
        """Like generate_proposals but returns metadata alongside the batch."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[PROPOSAL_TOOL],
                tool_choice={"type": "function", "function": {"name": "submit_proposals"}},
                temperature=0.2,
            )
        except Exception as e:
            raise LLMError(f"OpenAI API call failed: {e}") from e

        message = completion.choices[0].message
        if not message.tool_calls:
            raise LLMError(
                "LLM did not return a tool call. "
                f"Response content: {message.content[:200] if message.content else '(empty)'}"
            )

        tool_call = message.tool_calls[0]
        if tool_call.function.name != "submit_proposals":
            raise LLMError(f"Unexpected tool call: {tool_call.function.name}")

        try:
            raw_args = tool_call.function.arguments
            if isinstance(raw_args, str):
                parsed = json.loads(raw_args)
            else:
                parsed = raw_args
            batch = ProposalBatch.model_validate(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            raise LLMError(f"Failed to parse tool call arguments: {e}") from e

        usage = completion.usage
        return LLMResult(
            batch=batch,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            model=completion.model or self.model,
            content=message.content,
        )


@dataclass
class LLMResult:
    batch: ProposalBatch
    input_tokens: int
    output_tokens: int
    model: str
    content: str | None


class LLMError(Exception):
    """Raised when an LLM call fails or returns an unparseable response."""
