"""Tests for client.py — IntentClient and AsyncIntentClient."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from xingintent import Arg, AsyncIntentClient, Dialog, Intent, IntentClient, Schema
from xingintent.exceptions import APIError, ParseError, ValidationError


class TestSyncInit:
    def test_basic_init(self):
        client = IntentClient(base_url="http://localhost:8000/v1", model="test-model")
        assert client.model == "test-model"
        assert client.base_url == "http://localhost:8000/v1"
        assert client.api_key == ""

    def test_trailing_slash_stripped(self):
        client = IntentClient(base_url="http://localhost:8000/v1/", model="m")
        assert client.base_url == "http://localhost:8000/v1"

    def test_with_api_key(self):
        client = IntentClient(base_url="http://x", model="m", api_key="sk-xxx")
        assert client.api_key == "sk-xxx"

    def test_custom_headers(self):
        client = IntentClient(
            base_url="http://x", model="m",
            headers={"X-Custom-Header": "value"},
        )
        headers = client._build_headers()
        assert headers["X-Custom-Header"] == "value"

    def test_api_key_in_headers(self):
        client = IntentClient(base_url="http://x", model="m", api_key="sk-xxx")
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer sk-xxx"

    def test_custom_headers_merge_with_auth(self):
        client = IntentClient(
            base_url="http://x", model="m",
            api_key="sk-xxx",
            headers={"X-Api-Key": "custom"},
        )
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer sk-xxx"
        assert headers["X-Api-Key"] == "custom"

    def test_default_postprocessors(self):
        client = IntentClient(base_url="http://x", model="m")
        assert "arg_validate" in client.postprocessors

    def test_custom_postprocessors(self):
        client = IntentClient(
            base_url="http://x", model="m",
            postprocessors=["strip_markdown", "arg_validate"],
        )
        assert "strip_markdown" in client.postprocessors

    def test_default_system_prompt_is_none(self):
        client = IntentClient(base_url="http://x", model="m")
        assert client.system_prompt is None

    def test_custom_system_prompt(self):
        client = IntentClient(base_url="http://x", model="m", system_prompt="custom")
        assert client.system_prompt == "custom"

    def test_empty_system_prompt(self):
        client = IntentClient(base_url="http://x", model="m", system_prompt="")
        assert client.system_prompt == ""

    def test_custom_prompt_template(self):
        tmpl = "SCHEMA: {intent_descriptions}\nINPUT: {user_input}"
        client = IntentClient(base_url="http://x", model="m", prompt_template=tmpl)
        assert client.prompt_template == tmpl


class TestSyncPredict:
    @patch('xingintent.client.httpx.Client')
    def test_single_turn_success(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://localhost:8000/v1", model="test")
        result = client.predict(text="我要看第二个摄像头昨晚9点的云回放", intents=camera_intents)

        assert result.category == "查看摄像头回放"
        assert result.args["设备类型"] == "摄像头"
        assert result.args["时间"] == "昨晚9点"

    @patch('xingintent.client.httpx.Client')
    def test_multi_turn_success(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{
                "message": {"content": '[{"category": "查看摄像头直播", "args": [{"设备名称": "卧室"}]}]'},
                "finish_reason": "stop",
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        dialog = Dialog().human("我想看看摄像头画面。").ai("哪个房间？").human("卧室。")
        result = client.predict(dialog=dialog, intents=camera_intents)

        assert result.category == "查看摄像头直播"
        assert result.args["设备名称"] == "卧室"

    def test_neither_text_nor_dialog(self, camera_intents):
        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(ValueError, match="Either"):
            client.predict(intents=camera_intents)

    def test_both_text_and_dialog(self, camera_intents):
        client = IntentClient(base_url="http://x", model="m")
        dialog = Dialog().human("hi")
        with pytest.raises(ValueError, match="not both"):
            client.predict(text="hi", dialog=dialog, intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_api_error_non_200(self, mock_client_cls, camera_intents):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.is_success = False
        mock_resp.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="500"):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_request_error(self, mock_client_cls, camera_intents):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.RequestError("connection refused")
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="Request failed"):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_parse_error(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{"message": {"content": "not json"}, "finish_reason": "stop"}]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(ParseError):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_validation_error_unknown_category(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{
                "message": {"content": '[{"category": "不存在的", "args": []}]'},
                "finish_reason": "stop",
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(ValidationError, match="not in schema"):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_markdown_stripped(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{
                "message": {
                    "content": '```json\n[{"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]}]\n```'
                },
                "finish_reason": "stop",
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(
            base_url="http://x", model="m",
            postprocessors=["strip_markdown", "arg_validate"],
        )
        result = client.predict(text="看客厅", intents=camera_intents)
        assert result.category == "查看摄像头直播"
        assert result.args["设备名称"] == "客厅"

    @patch('xingintent.client.httpx.Client')
    def test_request_payload_has_fixed_params(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://localhost:8000/v1", model="test-model")
        client.predict(text="hi", intents=camera_intents)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == 128
        assert payload["chat_template_kwargs"] == {"enable_thinking": False}
        assert payload["model"] == "test-model"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"

    @patch('xingintent.client.httpx.Client')
    def test_accepts_schema_object(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        schema = Schema(camera_intents)
        client = IntentClient(base_url="http://x", model="m")
        result = client.predict(text="hi", intents=schema)
        assert result.category == "查看摄像头回放"

    @patch('xingintent.client.httpx.Client')
    def test_fallback_detection(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{
                "message": {"content": '[{"category": "其他意图", "args": []}]'},
                "finish_reason": "stop",
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        result = client.predict(text="abc", intents=camera_intents)
        assert result.is_fallback

    @patch('xingintent.client.httpx.Client')
    def test_guided_json_in_payload(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        client.predict(text="hi", intents=camera_intents, guided_json=True)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "response_format" in payload
        assert "guided_json" not in payload
        rf = payload["response_format"]
        assert rf["type"] == "json_schema"
        assert rf["json_schema"]["name"] == "intent_result"
        guided = rf["json_schema"]["schema"]
        assert guided["type"] == "array"
        categories = guided["items"]["properties"]["category"]["enum"]
        assert "查看摄像头直播" in categories
        assert "查看摄像头回放" in categories
        assert "其他意图" in categories

    @patch('xingintent.client.httpx.Client')
    def test_no_guided_json_by_default(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        client.predict(text="hi", intents=camera_intents)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "response_format" not in payload
        assert "guided_json" not in payload

    @patch('xingintent.client.httpx.Client')
    def test_custom_headers_sent(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(
            base_url="http://x", model="m",
            headers={"X-Token": "abc123"},
        )
        client.predict(text="hi", intents=camera_intents)

        call_args = mock_client.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["X-Token"] == "abc123"

    @patch('xingintent.client.httpx.Client')
    def test_empty_choices_raises_api_error(self, mock_client_cls, camera_intents):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = {"choices": []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="no choices"):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_json_decode_failure_raises_api_error(self, mock_client_cls, camera_intents):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_resp.text = "not json response"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="Failed to decode"):
            client.predict(text="hi", intents=camera_intents)

    @patch('xingintent.client.httpx.Client')
    def test_default_system_in_payload(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m")
        client.predict(text="hi", intents=camera_intents)

        payload = mock_client.post.call_args.kwargs["json"]
        messages = payload["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "TeleChat" in messages[0]["content"]

    @patch('xingintent.client.httpx.Client')
    def test_custom_system_in_payload(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m", system_prompt="my system")
        client.predict(text="hi", intents=camera_intents)

        payload = mock_client.post.call_args.kwargs["json"]
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "my system"

    @patch('xingintent.client.httpx.Client')
    def test_empty_system_no_system_message(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m", system_prompt="")
        client.predict(text="hi", intents=camera_intents)

        payload = mock_client.post.call_args.kwargs["json"]
        messages = payload["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @patch('xingintent.client.httpx.Client')
    def test_custom_template_in_payload(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        tmpl = "SCHEMA: {intent_descriptions}\nINPUT: {user_input}"
        client = IntentClient(base_url="http://x", model="m", prompt_template=tmpl)
        client.predict(text="hello", intents=camera_intents)

        payload = mock_client.post.call_args.kwargs["json"]
        user_content = payload["messages"][-1]["content"]
        assert user_content.startswith("SCHEMA:")
        assert "hello" in user_content
        assert "### 任务说明" not in user_content


class TestDebugMode:
    def test_debug_flag_default_false(self):
        client = IntentClient(base_url="http://x", model="m")
        assert client.debug is False

    def test_debug_flag_enabled(self):
        client = IntentClient(base_url="http://x", model="m", debug=True)
        assert client.debug is True

    @patch('xingintent.client.httpx.Client')
    def test_debug_emits_logs_on_success(self, mock_client_cls, camera_intents, mock_api_response, caplog):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response
        mock_resp.text = json.dumps(mock_api_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m", debug=True)
        with caplog.at_level("DEBUG", logger="xingintent"):
            client.predict(text="hi", intents=camera_intents)

        log_text = "\n".join(r.message for r in caplog.records)
        assert "predict started" in log_text
        assert "payload assembled" in log_text
        assert "sending request" in log_text
        assert "response received" in log_text
        assert "raw model output" in log_text
        assert "parsed predictions" in log_text
        assert "arg_validate applied" in log_text
        assert "result built" in log_text

    @patch('xingintent.client.httpx.Client')
    def test_debug_no_logs_when_disabled(self, mock_client_cls, camera_intents, mock_api_response, caplog):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response
        mock_resp.text = json.dumps(mock_api_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m", debug=False)
        with caplog.at_level("DEBUG", logger="xingintent"):
            client.predict(text="hi", intents=camera_intents)

        log_text = "\n".join(r.message for r in caplog.records)
        assert "predict started" not in log_text
        assert "payload assembled" not in log_text

    @patch('xingintent.client.httpx.Client')
    def test_debug_logs_on_api_error(self, mock_client_cls, camera_intents, caplog):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.is_success = False
        mock_resp.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = IntentClient(base_url="http://x", model="m", debug=True)
        with caplog.at_level("DEBUG", logger="xingintent"):
            with pytest.raises(APIError):
                client.predict(text="hi", intents=camera_intents)

        log_text = "\n".join(r.message for r in caplog.records)
        assert "non-200 response" in log_text


class TestAsyncPredict:
    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_single_turn_success(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(base_url="http://localhost:8000/v1", model="test")
        result = await client.predict(text="看摄像头回放", intents=camera_intents)

        assert result.category == "查看摄像头回放"

    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_multi_turn_success(self, mock_client_cls, camera_intents):
        api_resp = {
            "choices": [{
                "message": {"content": '[{"category": "查看摄像头直播", "args": [{"设备名称": "卧室"}]}]'},
                "finish_reason": "stop",
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = api_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(base_url="http://x", model="m")
        dialog = Dialog().human("看看摄像头").ai("哪个房间").human("卧室")
        result = await client.predict(dialog=dialog, intents=camera_intents)

        assert result.category == "查看摄像头直播"
        assert result.args["设备名称"] == "卧室"

    @pytest.mark.asyncio
    async def test_async_neither_text_nor_dialog(self, camera_intents):
        client = AsyncIntentClient(base_url="http://x", model="m")
        with pytest.raises(ValueError, match="Either"):
            await client.predict(intents=camera_intents)

    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_api_error(self, mock_client_cls, camera_intents):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.is_success = False
        mock_resp.text = "error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="500"):
            await client.predict(text="hi", intents=camera_intents)

    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_request_error(self, mock_client_cls, camera_intents):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.RequestError("connection refused")
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(base_url="http://x", model="m")
        with pytest.raises(APIError, match="Request failed"):
            await client.predict(text="hi", intents=camera_intents)

    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_guided_json(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(base_url="http://x", model="m")
        await client.predict(text="hi", intents=camera_intents, guided_json=True)

        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert "response_format" in payload
        assert payload["response_format"]["type"] == "json_schema"

    @pytest.mark.asyncio
    @patch('xingintent.client.httpx.AsyncClient')
    async def test_async_custom_headers(self, mock_client_cls, camera_intents, mock_api_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_success = True
        mock_resp.json.return_value = mock_api_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = AsyncIntentClient(
            base_url="http://x", model="m",
            headers={"X-Token": "abc"},
        )
        await client.predict(text="hi", intents=camera_intents)

        call_args = mock_client.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["X-Token"] == "abc"
