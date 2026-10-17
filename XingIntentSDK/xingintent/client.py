"""SDK clients for XingIntent model interaction.

Provides both synchronous and asynchronous clients:

- :class:`IntentClient` for blocking request/response patterns.
- :class:`AsyncIntentClient` for ``asyncio``-based applications.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from .dialog import Dialog
from .exceptions import APIError
from .guided import build_guided_schema
from .pipeline import arg_validate, parse_json, strip_markdown
from .prompt import build_messages
from .result import PredictResult
from .schema import Intent, Schema

logger = logging.getLogger("xingintent")


class _BaseClient:
    """Shared configuration and logic for sync/async clients."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        headers: Optional[Dict[str, str]] = None,
        max_tokens: int = 128,
        timeout: float = 30.0,
        postprocessors: Optional[List[str]] = None,
        debug: bool = False,
        system_prompt: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.postprocessors = postprocessors if postprocessors is not None else ["arg_validate"]
        self._extra_headers = headers or {}
        self.debug = debug
        self.system_prompt = system_prompt
        self.prompt_template = prompt_template
        if debug:
            logger.setLevel(logging.DEBUG)
            if not logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(
                    "%(asctime)s [%(levelname)s] xingintent: %(message)s",
                    datefmt="%H:%M:%S",
                ))
                logger.addHandler(handler)

    def _log_debug(self, msg: str, **kwargs: Any) -> None:
        if self.debug:
            extra = ""
            if kwargs:
                parts = []
                for k, v in kwargs.items():
                    s = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                    parts.append(f"{k}={s}")
                extra = " | " + ", ".join(parts)
            logger.debug(msg + extra)

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self._extra_headers)
        return headers

    def _build_payload(
        self,
        schema: Schema,
        user_input: Union[str, Dialog],
        guided_json: bool = False,
    ) -> Dict[str, Any]:
        messages = build_messages(
            schema, user_input,
            system_prompt=self.system_prompt,
            template=self.prompt_template,
        )
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if guided_json:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "intent_result",
                    "schema": build_guided_schema(schema),
                },
            }

        self._log_debug(
            "payload assembled",
            payload=payload,
        )
        return payload

    def _process_response(
        self,
        raw_response: Dict[str, Any],
        schema: Schema,
    ) -> PredictResult:
        content = self._extract_content(raw_response)

        self._log_debug("raw model output", content=content)

        if "strip_markdown" in self.postprocessors:
            before = content
            content = strip_markdown(content)
            if before != content:
                self._log_debug("strip_markdown applied", before=before, after=content)

        predictions = parse_json(content)

        self._log_debug("parsed predictions", predictions=predictions)

        if "arg_validate" in self.postprocessors:
            before_count = sum(len(p.get("args", [])) for p in predictions)
            predictions = arg_validate(predictions, schema)
            after_count = sum(len(p.get("args", [])) for p in predictions)
            self._log_debug(
                "arg_validate applied",
                categories=[p["category"] for p in predictions],
                arg_count_before=before_count,
                arg_count_after=after_count,
            )

        fallback_category = ""
        for intent in schema:
            if intent.is_fallback:
                fallback_category = intent.category
                break

        result = PredictResult(predictions, fallback_category=fallback_category)

        self._log_debug(
            "result built",
            category=result.category,
            is_fallback=result.is_fallback,
            is_multi=result.is_multi,
        )
        return result

    @staticmethod
    def _extract_content(response: Dict[str, Any]) -> str:
        try:
            choices = response["choices"]
            if not choices:
                raise APIError("Response has no choices")
            content = choices[0]["message"]["content"]
            if content is None:
                raise APIError("Response message content is None")
            return content
        except (KeyError, IndexError) as e:
            raise APIError(f"Unexpected response structure: missing {e}")

    @staticmethod
    def _resolve_schema(intents: Union[List[Intent], Schema]) -> Schema:
        if isinstance(intents, Schema):
            return intents
        return Schema(list(intents))


class IntentClient(_BaseClient):
    """Synchronous client for the XingIntent model.

    Args:
        base_url: Base URL of the model API.
        model: Model name.
        api_key: Optional API key for authentication.
        headers: Additional HTTP headers.
        max_tokens: Maximum tokens for model response.
        timeout: Request timeout in seconds.
        postprocessors: Postprocessor names to apply.
        debug: When True, enables debug logging of the internal pipeline.
        system_prompt: System message content. Defaults to the built-in
            TeleChat identity prompt. Pass an empty string to omit.
        prompt_template: Custom user prompt template with {intent_descriptions}
            and {user_input} placeholders. Defaults to the built-in template.
    """

    def predict(
        self,
        intents: Union[List[Intent], Schema],
        text: Optional[str] = None,
        dialog: Optional[Dialog] = None,
        guided_json: bool = False,
    ) -> PredictResult:
        """Run intent prediction.

        Exactly one of ``text`` or ``dialog`` must be provided.

        Args:
            intents: List of Intent objects or a Schema instance.
            text: Plain text input for single-turn prediction.
            dialog: Dialog instance for multi-turn prediction.
            guided_json: When True, sends a JSON Schema to vLLM for
                constrained decoding to improve output stability.

        Returns:
            PredictResult with structured prediction data.

        Raises:
            ValueError: If neither or both of text/dialog are provided.
            APIError: If the model API request fails.
            ParseError: If the response cannot be parsed.
            ValidationError: If the result fails schema validation.
        """
        if text is None and dialog is None:
            raise ValueError("Either 'text' or 'dialog' must be provided")
        if text is not None and dialog is not None:
            raise ValueError("Provide 'text' or 'dialog', not both")

        schema = self._resolve_schema(intents)
        user_input = dialog if dialog is not None else text

        self._log_debug(
            "predict started",
            input_type="dialog" if dialog is not None else "text",
            schema_categories=schema.get_categories(),
        )

        payload = self._build_payload(schema, user_input, guided_json)
        raw_response = self._send_request(payload)
        return self._process_response(raw_response, schema)

    def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        self._log_debug("sending request", url=url)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.RequestError as e:
            self._log_debug("request failed", error=str(e))
            raise APIError(f"Request failed: {e}")
        except httpx.HTTPError as e:
            self._log_debug("http error", error=str(e))
            raise APIError(f"HTTP error: {e}")

        self._log_debug(
            "response received",
            status_code=resp.status_code,
            response_length=len(resp.text),
        )

        if not resp.is_success:
            self._log_debug("non-200 response", body=resp.text[:500])
            raise APIError(
                f"API returned status {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            self._log_debug("json decode failed", body=resp.text[:500])
            raise APIError(
                f"Failed to decode JSON response: {e}",
                response_body=resp.text,
            )


class AsyncIntentClient(_BaseClient):
    """Asynchronous client for the XingIntent model.

    Uses ``httpx.AsyncClient`` for non-blocking requests.

    Args:
        Same as :class:`IntentClient`.
    """

    async def predict(
        self,
        intents: Union[List[Intent], Schema],
        text: Optional[str] = None,
        dialog: Optional[Dialog] = None,
        guided_json: bool = False,
    ) -> PredictResult:
        """Run intent prediction asynchronously.

        Same parameters and behavior as :meth:`IntentClient.predict`,
        but returns a coroutine.
        """
        if text is None and dialog is None:
            raise ValueError("Either 'text' or 'dialog' must be provided")
        if text is not None and dialog is not None:
            raise ValueError("Provide 'text' or 'dialog', not both")

        schema = self._resolve_schema(intents)
        user_input = dialog if dialog is not None else text

        self._log_debug(
            "predict started",
            input_type="dialog" if dialog is not None else "text",
            schema_categories=schema.get_categories(),
        )

        payload = self._build_payload(schema, user_input, guided_json)
        raw_response = await self._send_request(payload)
        return self._process_response(raw_response, schema)

    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        self._log_debug("sending async request", url=url)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as e:
            self._log_debug("request failed", error=str(e))
            raise APIError(f"Request failed: {e}")
        except httpx.HTTPError as e:
            self._log_debug("http error", error=str(e))
            raise APIError(f"HTTP error: {e}")

        self._log_debug(
            "response received",
            status_code=resp.status_code,
            response_length=len(resp.text),
        )

        if not resp.is_success:
            self._log_debug("non-200 response", body=resp.text[:500])
            raise APIError(
                f"API returned status {resp.status_code}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            self._log_debug("json decode failed", body=resp.text[:500])
            raise APIError(
                f"Failed to decode JSON response: {e}",
                response_body=resp.text,
            )
