"""Tests for the LLM client — verifies parsing/validation without real API calls."""

from unittest.mock import MagicMock, patch

import pytest

from app.llm.client import LLMClient, LLMError
from app.llm.schemas import ProposalBatch


def _make_completion(arguments, tool_name="submit_proposals"):
    """Build a mock OpenAI completion response."""
    tool_call = MagicMock()
    tool_call.function.name = tool_name
    tool_call.function.arguments = arguments

    message = MagicMock()
    message.tool_calls = [tool_call]
    message.content = None

    choice = MagicMock()
    choice.message = message

    completion = MagicMock()
    completion.choices = [choice]
    completion.model = "anthropic/claude-sonnet-4-6"
    completion.usage.total_tokens = 500

    return completion


@patch("app.llm.client.OpenAI")
def test_generate_proposals_parses_valid_response(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.return_value = _make_completion(
        '{"proposals": [{"proposal_type": "create_task", "proposed_title": "Fix login bug", "reason_summary": "Found in GitHub issue #42"}]}'
    )

    client = LLMClient(model="anthropic/claude-sonnet-4-6")
    batch = client.generate_proposals("system prompt", "user prompt")

    assert isinstance(batch, ProposalBatch)
    assert len(batch.proposals) == 1
    assert batch.proposals[0].proposal_type == "create_task"
    assert batch.proposals[0].proposed_title == "Fix login bug"

    # Verify the API was called with correct structure
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "anthropic/claude-sonnet-4-6"
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["function"]["name"] == "submit_proposals"
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "submit_proposals"},
    }


@patch("app.llm.client.OpenAI")
def test_generate_proposals_handles_dict_arguments(mock_dedalus_cls):
    """Some providers return arguments as a dict instead of a JSON string."""
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.return_value = _make_completion(
        {
            "proposals": [
                {
                    "proposal_type": "change_status",
                    "task_id": 7,
                    "proposed_status": "done",
                    "reason_summary": "PR merged",
                }
            ]
        }
    )

    client = LLMClient()
    batch = client.generate_proposals("system", "user")

    assert batch.proposals[0].proposed_status == "done"
    assert batch.proposals[0].task_id == 7


@patch("app.llm.client.OpenAI")
def test_generate_proposals_raises_on_no_tool_calls(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    message = MagicMock()
    message.tool_calls = []
    message.content = "I can't do that"
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    mock_client.chat.completions.create.return_value = completion

    client = LLMClient()
    with pytest.raises(LLMError, match="did not return a tool call"):
        client.generate_proposals("system", "user")


@patch("app.llm.client.OpenAI")
def test_generate_proposals_raises_on_invalid_json(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.return_value = _make_completion("not valid json{{{")

    client = LLMClient()
    with pytest.raises(LLMError, match="Failed to parse"):
        client.generate_proposals("system", "user")


@patch("app.llm.client.OpenAI")
def test_generate_proposals_raises_on_api_error(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.side_effect = RuntimeError("connection timeout")

    client = LLMClient()
    with pytest.raises(LLMError, match="OpenAI API call failed"):
        client.generate_proposals("system", "user")


@patch("app.llm.client.OpenAI")
def test_generate_proposals_raises_on_wrong_tool_name(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.return_value = _make_completion(
        '{"proposals": []}', tool_name="wrong_tool"
    )

    client = LLMClient()
    with pytest.raises(LLMError, match="Unexpected tool call"):
        client.generate_proposals("system", "user")


@patch("app.llm.client.OpenAI")
def test_generate_proposals_validates_enum_values(mock_dedalus_cls):
    mock_client = MagicMock()
    mock_dedalus_cls.return_value = mock_client

    mock_client.chat.completions.create.return_value = _make_completion(
        '{"proposals": [{"proposal_type": "invalid_type"}]}'
    )

    client = LLMClient()
    with pytest.raises(LLMError, match="Failed to parse"):
        client.generate_proposals("system", "user")
