"""Tests for guided.py — vLLM JSON Schema generation."""

from xingintent import Arg, Intent, Schema
from xingintent.guided import build_guided_schema


class TestBuildGuidedSchema:
    def test_basic_structure(self, camera_schema):
        s = build_guided_schema(camera_schema)
        assert s["type"] == "array"
        assert "items" in s

    def test_items_structure(self, camera_schema):
        s = build_guided_schema(camera_schema)
        items = s["items"]
        assert items["type"] == "object"
        assert "category" in items["properties"]
        assert "args" in items["properties"]
        assert items["required"] == ["category", "args"]

    def test_category_enum(self, camera_schema):
        s = build_guided_schema(camera_schema)
        categories = s["items"]["properties"]["category"]["enum"]
        assert "查看摄像头直播" in categories
        assert "查看摄像头回放" in categories
        assert "其他意图" in categories

    def test_args_is_array(self, camera_schema):
        s = build_guided_schema(camera_schema)
        args_prop = s["items"]["properties"]["args"]
        assert args_prop["type"] == "array"
        assert "items" in args_prop

    def test_additional_properties_false(self, camera_schema):
        s = build_guided_schema(camera_schema)
        assert s["items"]["additionalProperties"] is False

    def test_no_args_intent(self):
        schema = Schema([
            Intent("意图A", "desc A", args=[]),
            Intent.fallback("其他"),
        ])
        s = build_guided_schema(schema)
        assert s["type"] == "array"
        categories = s["items"]["properties"]["category"]["enum"]
        assert "意图A" in categories

    def test_single_intent_with_args(self):
        schema = Schema([
            Intent("意图A", "desc A", args=[Arg("x", "param x")]),
        ])
        s = build_guided_schema(schema)
        args_item = s["items"]["properties"]["args"]["items"]
        assert args_item["type"] == "object"
        assert "x" in args_item["properties"]

    def test_multiple_intents_with_args(self, camera_schema):
        s = build_guided_schema(camera_schema)
        args_item = s["items"]["properties"]["args"]["items"]
        # Multiple intents with args -> anyOf
        assert "anyOf" in args_item

    def test_all_categories_in_enum(self, camera_schema):
        s = build_guided_schema(camera_schema)
        enum = set(s["items"]["properties"]["category"]["enum"])
        expected = set(camera_schema.get_categories())
        assert enum == expected
