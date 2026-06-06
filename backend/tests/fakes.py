"""In-memory test doubles. No test ever touches the network."""

from typing import TypeVar, cast

from pydantic import BaseModel

from app import constants
from app.errors import RealtimeUnavailableError
from app.schemas import RealtimeTokenResponse

T = TypeVar("T", bound=BaseModel)


class FakeGateway:
    """AIGateway double returning pre-seeded structured outputs."""

    def __init__(
        self,
        *,
        configured: bool = True,
        outputs: dict[type[BaseModel], BaseModel] | None = None,
        fail_schemas: set[str] | None = None,
    ) -> None:
        self._configured = configured
        self.outputs = outputs or {}
        self.fail_schemas = fail_schemas or set()
        self.calls: list[str] = []
        self.last_content: str | list[dict[str, object]] | None = None

    @property
    def configured(self) -> bool:
        return self._configured

    def _resolve(self, schema: type[T]) -> T:
        if schema.__name__ in self.fail_schemas:
            msg = f"simulated {schema.__name__} failure"
            raise RuntimeError(msg)
        if schema not in self.outputs:
            msg = f"no fake output seeded for {schema.__name__}"
            raise RuntimeError(msg)
        return cast(T, self.outputs[schema])

    async def parse_structured(
        self,
        *,
        model: str,
        instructions: str,
        content: str | list[dict[str, object]],
        schema: type[T],
    ) -> T:
        self.calls.append(f"structured:{model}:{schema.__name__}")
        self.last_content = content
        return self._resolve(schema)

    async def audio_json(
        self,
        *,
        model: str,
        prompt: str,
        audio_b64: str,
        audio_format: str,
        schema: type[T],
    ) -> T:
        self.calls.append(f"audio:{model}:{schema.__name__}")
        return self._resolve(schema)

    async def mint_realtime_secret(self) -> RealtimeTokenResponse:
        if not self._configured:
            raise RealtimeUnavailableError("Voice mode is unavailable in tests")
        return RealtimeTokenResponse(
            value="ek_test_token", expires_at=1_900_000_000, model=constants.REALTIME_MODEL
        )


class RecordingEmailSender:
    """EmailSender double that records sends."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class FailingEmailSender:
    """EmailSender double whose delivery always fails."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        msg = "simulated SMTP failure"
        raise ConnectionError(msg)
