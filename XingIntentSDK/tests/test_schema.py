"""Tests for schema.py — Intent, Arg, Schema."""

import json
import os
import tempfile

import pytest

from xingintent import Arg, Intent, Schema
from xingintent.exceptions import SchemaError


class TestArg:
    def test_basic_creation(self):
        arg = Arg("设备名称", "设备的位置")
        assert arg.name == "设备名称"
        assert arg.description == "设备的位置"

    def test_to_dict(self):
        arg = Arg("时间", "时间段")
        d = arg.to_dict()
        assert d == {"name": "时间", "description": "时间段"}

    def test_empty_name_raises(self):
        with pytest.raises(SchemaError, match="cannot be empty"):
            Arg("", "description")

    def test_equality(self):
        a1 = Arg("x", "desc")
        a2 = Arg("x", "desc")
        a3 = Arg("x", "different")
        assert a1 == a2
        assert a1 != a3


class TestIntent:
    def test_basic_creation(self):
        intent = Intent("查看摄像头", "用户想看摄像头", args=[Arg("位置", "设备位置")])
        assert intent.category == "查看摄像头"
        assert intent.description == "用户想看摄像头"
        assert len(intent.args) == 1

    def test_no_args_defaults_to_empty(self):
        intent = Intent("测试", "测试意图")
        assert intent.args == []

    def test_fallback(self):
        intent = Intent.fallback("其他意图")
        assert intent.category == "其他意图"
        assert "无法匹配" in intent.description
        assert intent.args == []

    def test_fallback_default_name(self):
        intent = Intent.fallback()
        assert intent.category == "其他意图"

    def test_from_dict(self):
        d = {
            "category": "查看直播",
            "category_description": "实时查看",
            "args": [{"name": "位置", "description": "位置信息"}],
        }
        intent = Intent.from_dict(d)
        assert intent.category == "查看直播"
        assert intent.description == "实时查看"
        assert intent.args[0].name == "位置"

    def test_from_dict_no_args(self):
        d = {"category": "其他", "category_description": "兜底"}
        intent = Intent.from_dict(d)
        assert intent.args == []

    def test_to_dict_roundtrip(self):
        intent = Intent("x", "desc", args=[Arg("a", "b")])
        d = intent.to_dict()
        intent2 = Intent.from_dict(d)
        assert intent == intent2

    def test_empty_category_raises(self):
        with pytest.raises(SchemaError, match="cannot be empty"):
            Intent("", "desc")

    def test_repr(self):
        intent = Intent("x", "d", args=[Arg("a", "b")])
        assert "Intent" in repr(intent)
        assert "x" in repr(intent)


class TestSchema:
    def test_from_list(self, camera_intents):
        schema = Schema(camera_intents)
        assert len(schema) == 3

    def test_from_json_string(self, camera_intents):
        json_str = json.dumps([i.to_dict() for i in camera_intents], ensure_ascii=False)
        schema = Schema.from_json(json_str)
        assert len(schema) == 3
        assert schema[0].category == "查看摄像头直播"

    def test_from_json_file(self, camera_intents):
        data = [i.to_dict() for i in camera_intents]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name

        try:
            schema = Schema.from_json(path)
            assert len(schema) == 3
        finally:
            os.unlink(path)

    def test_from_parsed_list(self, camera_intents):
        data = [i.to_dict() for i in camera_intents]
        schema = Schema.from_json(data)
        assert len(schema) == 3

    def test_to_json_compact(self, camera_schema):
        s = camera_schema.to_json()
        assert isinstance(s, str)
        # Compact: no newlines between items
        parsed = json.loads(s)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_get_categories(self, camera_schema):
        cats = camera_schema.get_categories()
        assert "查看摄像头直播" in cats
        assert "查看摄像头回放" in cats
        assert "其他意图" in cats

    def test_get_arg_names(self, camera_schema):
        names = camera_schema.get_arg_names("查看摄像头回放")
        assert "设备类型" in names
        assert "时间" in names
        assert len(names) == 4

    def test_get_arg_names_unknown_category(self, camera_schema):
        assert camera_schema.get_arg_names("不存在") == []

    def test_find_intent(self, camera_schema):
        intent = camera_schema.find_intent("查看摄像头直播")
        assert intent is not None
        assert intent.category == "查看摄像头直播"

    def test_find_intent_not_found(self, camera_schema):
        assert camera_schema.find_intent("不存在") is None

    def test_iteration(self, camera_schema):
        cats = [i.category for i in camera_schema]
        assert len(cats) == 3

    def test_empty_schema_raises(self):
        with pytest.raises(SchemaError, match="at least one"):
            Schema([])
