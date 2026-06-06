"""Shared OpenAI access. Every OpenAI call in the app goes through here.

The ``AIGateway`` protocol lets services depend on an interface, so tests
inject fakes and no test ever touches the network.
"""

from typing import Any, Protocol, TypeVar, cast

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from app import constants
from app.config import Settings
from app.errors import RealtimeUnavailableError, UpstreamServiceError
from app.schemas import RealtimeTokenResponse

T = TypeVar("T", bound=BaseModel)

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_TOKEN_TTL_SECONDS = 600
_REQUEST_TIMEOUT_SECONDS = 30.0


class AIGateway(Protocol):
    """Interface for AI calls, implemented by ``OpenAIGateway`` and test fakes."""

    @property
    def configured(self) -> bool:
        """Whether AI-backed features are available (else stub modes)."""
        ...

    async def parse_structured(
        self,
        *,
        model: str,
        instructions: str,
        content: str | list[dict[str, object]],
        schema: type[T],
    ) -> T:
        """Structured-output call via the Responses API."""
        ...

    async def audio_json(
        self,
        *,
        model: str,
        prompt: str,
        audio_b64: str,
        audio_format: str,
        schema: type[T],
    ) -> T:
        """Audio-input call via Chat Completions, parsed into ``schema``."""
        ...

    async def mint_realtime_secret(
        self, *, instructions: str, ttl_seconds: int
    ) -> RealtimeTokenResponse:
        """Mint a short-lived realtime client secret (GA flow)."""
        ...


def _extract_json(text: str) -> str:
    """Pull the JSON object out of a possibly fenced/wrapped model reply."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise UpstreamServiceError("model returned no JSON object")
    return text[start : end + 1]


class OpenAIGateway:
    """Production gateway backed by the OpenAI API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openai_api_key
        self._client = AsyncOpenAI(api_key=self._api_key) if settings.openai_configured else None

    @property
    def configured(self) -> bool:
        """Whether an API key is present."""
        return self._client is not None

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise UpstreamServiceError("OpenAI is not configured")
        return self._client

    async def parse_structured(
        self,
        *,
        model: str,
        instructions: str,
        content: str | list[dict[str, object]],
        schema: type[T],
    ) -> T:
        """Call the Responses API with structured output (low reasoning effort)."""
        client = self._require_client()
        extra: dict[str, Any] = {}
        if model.startswith("gpt-5"):
            extra["reasoning"] = {"effort": "low"}
        input_param: Any = (
            content if isinstance(content, str) else [{"role": "user", "content": content}]
        )
        response = await client.responses.parse(
            model=model,
            instructions=instructions,
            input=input_param,
            text_format=schema,
            timeout=_REQUEST_TIMEOUT_SECONDS,
            **extra,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise UpstreamServiceError("model returned no structured output")
        return parsed

    async def audio_json(
        self,
        *,
        model: str,
        prompt: str,
        audio_b64: str,
        audio_format: str,
        schema: type[T],
    ) -> T:
        """Send a short audio clip and parse the model's JSON-only reply."""
        client = self._require_client()
        messages: Any = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": audio_format},
                    },
                ],
            }
        ]
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        text = completion.choices[0].message.content or ""
        return schema.model_validate_json(_extract_json(text))

    async def mint_realtime_secret(
        self, *, instructions: str, ttl_seconds: int = _TOKEN_TTL_SECONDS
    ) -> RealtimeTokenResponse:
        """Mint an ephemeral client secret for the browser's realtime session.

        Uses the GA endpoint (``POST /v1/realtime/client_secrets``); the
        session model and instructions are pinned server-side so the browser
        can never change them. ``ttl_seconds`` doubles as a server-side cap
        on session length (e.g. the 70s calming-companion backstop).
        """
        if not self.configured:
            raise RealtimeUnavailableError(
                "Voice mode is unavailable: no OpenAI key configured on the server."
            )
        body = {
            "expires_after": {"anchor": "created_at", "seconds": ttl_seconds},
            "session": {
                "type": "realtime",
                "model": constants.REALTIME_MODEL,
                "instructions": instructions,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as http:
                response = await http.post(
                    f"{_OPENAI_BASE_URL}/realtime/client_secrets",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise RealtimeUnavailableError("Could not start a voice session right now.") from exc
        if response.status_code != httpx.codes.OK:
            raise RealtimeUnavailableError("Could not start a voice session right now.")
        data = response.json()
        return RealtimeTokenResponse(
            value=cast(str, data["value"]),
            expires_at=cast(int, data["expires_at"]),
            model=constants.REALTIME_MODEL,
        )
