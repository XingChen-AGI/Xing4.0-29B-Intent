"""Tests for result.py — PredictResult and IntentResult."""

from xingintent import IntentResult, PredictResult


class TestIntentResult:
    def test_basic_creation(self):
        r = IntentResult(category="x", args=[{"a": "1"}])
        assert r.category == "x"
        assert r.args == [{"a": "1"}]

    def test_args_flat_single(self):
        r = IntentResult(category="x", args=[{"a": "1", "b": "2"}])
        assert r.args_flat == {"a": "1", "b": "2"}

    def test_args_flat_multi_merge(self):
        r = IntentResult(category="x", args=[{"a": "1"}, {"b": "2"}])
        assert r.args_flat == {"a": "1", "b": "2"}

    def test_args_flat_merge_overwrite(self):
        r = IntentResult(category="x", args=[{"a": "1"}, {"a": "2"}])
        assert r.args_flat == {"a": "2"}

    def test_empty_args(self):
        r = IntentResult(category="x")
        assert r.is_empty_args
        assert r.args_flat == {}

    def test_get_method(self):
        r = IntentResult(category="x", args=[{"a": "1"}])
        assert r.get("a") == "1"
        assert r.get("b") == ""
        assert r.get("b", "default") == "default"

    def test_item_access(self):
        r = IntentResult(category="x", args=[{"时间": "昨天"}])
        assert r["时间"] == "昨天"

    def test_contains(self):
        r = IntentResult(category="x", args=[{"a": "1"}])
        assert "a" in r
        assert "b" not in r

    def test_eq(self):
        r1 = IntentResult("x", [{"a": "1"}])
        r2 = IntentResult("x", [{"a": "1"}])
        r3 = IntentResult("y", [{"a": "1"}])
        assert r1 == r2
        assert r1 != r3

    def test_repr(self):
        r = IntentResult("x", [{"a": "1"}])
        assert "IntentResult" in repr(r)
        assert "x" in repr(r)


class TestPredictResult:
    def test_single_prediction(self, sample_predictions):
        result = PredictResult(sample_predictions)
        assert len(result) == 1
        assert result.category == "查看摄像头回放"
        assert result.args["设备类型"] == "摄像头"

    def test_multi_prediction(self, multi_predictions):
        result = PredictResult(multi_predictions)
        assert result.is_multi
        assert len(result) == 2
        assert result.intents[0].category == "查看摄像头直播"
        assert result.intents[1].category == "查看摄像头回放"

    def test_fallback_detection(self, fallback_predictions):
        result = PredictResult(fallback_predictions, fallback_category="其他意图")
        assert result.is_fallback

    def test_not_fallback(self, sample_predictions):
        result = PredictResult(sample_predictions, fallback_category="其他意图")
        assert not result.is_fallback

    def test_get_method(self, sample_predictions):
        result = PredictResult(sample_predictions)
        assert result.get("设备类型") == "摄像头"
        assert result.get("不存在", "default") == "default"

    def test_iteration(self, multi_predictions):
        result = PredictResult(multi_predictions)
        cats = [r.category for r in result]
        assert len(cats) == 2
        assert "查看摄像头直播" in cats

    def test_indexing(self, multi_predictions):
        result = PredictResult(multi_predictions)
        assert result[0].category == "查看摄像头直播"

    def test_raw_preserved(self, sample_predictions):
        result = PredictResult(sample_predictions)
        assert result.raw == sample_predictions

    def test_empty_predictions(self):
        result = PredictResult([])
        assert len(result) == 0
        assert result.category == ""
        assert result.args == {}

    def test_repr_single(self, sample_predictions):
        result = PredictResult(sample_predictions)
        r = repr(result)
        assert "PredictResult" in r
        assert "查看摄像头回放" in r

    def test_repr_multi(self, multi_predictions):
        result = PredictResult(multi_predictions)
        r = repr(result)
        assert "PredictResult" in r
        assert "intents" in r
