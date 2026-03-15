"""LLM client wrapper.

Wraps the Anthropic API for structured proposal generation. All model
calls in the system go through this module so retry logic, model
selection, token tracking, and error handling are centralized.

Responsibilities:
- initialize Anthropic client from settings
- call the model with a prompt payload and constrained output schema
- return validated structured output
- log token usage and model metadata for debugging

TODO: decide exact function-calling / structured-output pattern (tech spec §12 TODO)
TODO: implement retry logic for transient API errors
"""


class LLMClient:
    def __init__(self) -> None:
        # TODO: initialize anthropic.Anthropic(api_key=settings.anthropic_api_key)
        pass

    def generate_proposals(self, prompt: str, schema: dict) -> list[dict]:
        # TODO: call model with schema-constrained output; validate response; return proposal dicts
        raise NotImplementedError
