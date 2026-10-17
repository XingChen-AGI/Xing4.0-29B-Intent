"""Tests for prompt.py — prompt assembly."""

import json
import re

from xingintent import Arg, Dialog, Intent, Schema
from xingintent.prompt import DEFAULT_SYSTEM_PROMPT, build_messages, build_prompt


class TestBuildPrompt:
    def test_single_turn_text(self, camera_schema):
        prompt = build_prompt(camera_schema, "我要看客厅的摄像头")

        assert "### 任务说明" in prompt
        assert "### 字段说明" in prompt
        assert "### 输入内容" in prompt
        assert "我要看客厅的摄像头" in prompt

    def test_schema_is_compact_json(self, camera_schema):
        prompt = build_prompt(camera_schema, "test")
        # Extract the schema section
        match = re.search(r'### 字段说明\n\n(.*?)\n\n### 输入内容', prompt, re.DOTALL)
        assert match is not None
        schema_text = match.group(1)
        # Must be valid JSON
        parsed = json.loads(schema_text)
        assert isinstance(parsed, list)
        # Must contain expected categories
        cats = [item["category"] for item in parsed]
        assert "查看摄像头直播" in cats

    def test_multi_turn_dialog(self, camera_schema):
        dialog = (
            Dialog()
            .human("我想看看摄像头画面。")
            .ai("你想查看哪个房间？")
            .human("卧室。")
        )
        prompt = build_prompt(camera_schema, dialog)

        assert "Human: 我想看看摄像头画面。" in prompt
        assert "AI: 你想查看哪个房间？" in prompt
        assert "Human: 卧室。" in prompt

    def test_no_placeholders_remain(self, camera_schema):
        prompt = build_prompt(camera_schema, "test")
        assert "{intent_descriptions}" not in prompt
        assert "{user_input}" not in prompt

    def test_template_structure(self, camera_schema):
        prompt = build_prompt(camera_schema, "test")
        # Sections must appear in correct order
        idx_task = prompt.index("### 任务说明")
        idx_schema = prompt.index("### 字段说明")
        idx_input = prompt.index("### 输入内容")
        assert idx_task < idx_schema < idx_input

    def test_output_format_in_template(self, camera_schema):
        prompt = build_prompt(camera_schema, "test")
        assert "category" in prompt
        assert "args" in prompt

    def test_custom_template(self, camera_schema):
        custom = "SCHEMA: {intent_descriptions}\nINPUT: {user_input}"
        prompt = build_prompt(camera_schema, "hello", template=custom)
        assert prompt.startswith("SCHEMA:")
        assert "hello" in prompt
        assert "### 任务说明" not in prompt


class TestBuildMessages:
    def test_default_has_system_message(self, camera_schema):
        messages = build_messages(camera_schema, "test")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == DEFAULT_SYSTEM_PROMPT
        assert messages[1]["role"] == "user"

    def test_custom_system_prompt(self, camera_schema):
        messages = build_messages(camera_schema, "test", system_prompt="custom system")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "custom system"

    def test_empty_system_omits_message(self, camera_schema):
        messages = build_messages(camera_schema, "test", system_prompt="")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_none_system_uses_default(self, camera_schema):
        messages = build_messages(camera_schema, "test", system_prompt=None)
        assert len(messages) == 2
        assert messages[0]["content"] == DEFAULT_SYSTEM_PROMPT

    def test_dialog_messages(self, camera_schema):
        dialog = Dialog().human("hi").ai("hello").human("bye")
        messages = build_messages(camera_schema, dialog)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Human: hi" in messages[1]["content"]
        assert "AI: hello" in messages[1]["content"]
        assert "Human: bye" in messages[1]["content"]

    def test_default_system_prompt_content(self):
        assert "TeleChat" in DEFAULT_SYSTEM_PROMPT
        assert "中国电信" in DEFAULT_SYSTEM_PROMPT
