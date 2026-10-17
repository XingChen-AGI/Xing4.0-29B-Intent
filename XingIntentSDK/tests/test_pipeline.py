"""Tests for pipeline.py — post-processing."""

import pytest

from xingintent import Schema
from xingintent.pipeline import arg_validate, get_postprocessor, parse_json, strip_markdown
from xingintent.exceptions import ParseError, ValidationError


class TestStripMarkdown:
    def test_plain_json(self):
        assert strip_markdown('[{"category": "test"}]') == '[{"category": "test"}]'

    def test_markdown_fenced_json(self):
        text = '```json\n[{"category": "test"}]\n```'
        assert strip_markdown(text) == '[{"category": "test"}]'

    def test_markdown_fenced_no_lang(self):
        text = '```\n[{"category": "test"}]\n```'
        assert strip_markdown(text) == '[{"category": "test"}]'

    def test_with_leading_whitespace(self):
        text = '  [{"category": "test"}]  '
        assert strip_markdown(text) == '[{"category": "test"}]'


class TestParseJson:
    def test_valid_array(self):
        content = '[{"category": "x", "args": []}]'
        result = parse_json(content)
        assert len(result) == 1
        assert result[0]["category"] == "x"

    def test_single_object_wrapped(self):
        content = '{"category": "x", "args": []}'
        result = parse_json(content)
        assert len(result) == 1

    def test_markdown_wrapped(self):
        content = '```json\n[{"category": "x"}]\n```'
        result = parse_json(content)
        assert len(result) == 1

    def test_json_embedded_in_text(self):
        content = '这是结果：[{"category": "x", "args": []}] 谢谢'
        result = parse_json(content)
        assert result[0]["category"] == "x"

    def test_empty_content_raises(self):
        with pytest.raises(ParseError, match="Empty"):
            parse_json("")

    def test_invalid_json_raises(self):
        with pytest.raises(ParseError):
            parse_json("not json at all")

    def test_no_array_raises(self):
        with pytest.raises(ParseError, match="No JSON array"):
            parse_json("just plain text with no json at all")


class TestArgValidate:
    def test_valid_prediction(self, camera_schema):
        predictions = [
            {"category": "查看摄像头回放", "args": [{"设备类型": "摄像头", "时间": "昨天"}]}
        ]
        result = arg_validate(predictions, camera_schema)
        assert result[0]["args"][0]["设备类型"] == "摄像头"

    def test_filters_invalid_arg_names(self, camera_schema):
        predictions = [
            {"category": "查看摄像头回放", "args": [{"设备类型": "摄像头", "无效字段": "x"}]}
        ]
        result = arg_validate(predictions, camera_schema)
        assert "设备类型" in result[0]["args"][0]
        assert "无效字段" not in result[0]["args"][0]

    def test_unknown_category_raises(self, camera_schema):
        predictions = [{"category": "不存在的意图", "args": []}]
        with pytest.raises(ValidationError, match="not in schema"):
            arg_validate(predictions, camera_schema)

    def test_empty_args_preserved(self, camera_schema):
        predictions = [{"category": "其他意图", "args": []}]
        result = arg_validate(predictions, camera_schema)
        assert result[0]["args"] == []

    def test_multiple_arg_instances(self, camera_schema):
        predictions = [
            {"category": "查看摄像头回放", "args": [{"设备类型": "摄像头"}, {"时间": "昨天"}]}
        ]
        result = arg_validate(predictions, camera_schema)
        assert len(result[0]["args"]) == 2


class TestGetPostprocessor:
    def test_known_processors(self):
        assert get_postprocessor("strip_markdown") is strip_markdown
        assert get_postprocessor("arg_validate") is arg_validate

    def test_unknown_processor(self):
        with pytest.raises(ValueError, match="Unknown postprocessor"):
            get_postprocessor("nonexistent")
