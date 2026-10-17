"""Shared test fixtures."""

import pytest

from xingintent import Arg, Intent, Schema


@pytest.fixture
def camera_intents():
    """Standard camera intent set used across tests."""
    return [
        Intent(
            category="查看摄像头直播",
            description="用户想要实时查看摄像头等设备的当前实时画面。",
            args=[Arg("设备名称", "设备名称或位置")],
        ),
        Intent(
            category="查看摄像头回放",
            description="用户想要查看设备的回看或存储画面。",
            args=[
                Arg("设备类型", "摄像头、门铃等"),
                Arg("位置", "设备所在位置"),
                Arg("时间", "回放时间段"),
                Arg("设备序号", "第X个设备的序号"),
            ],
        ),
        Intent.fallback("其他意图"),
    ]


@pytest.fixture
def camera_schema(camera_intents):
    return Schema(camera_intents)


@pytest.fixture
def sample_predictions():
    """Sample model prediction output (single intent with args)."""
    return [
        {
            "category": "查看摄像头回放",
            "args": [
                {"设备类型": "摄像头", "设备序号": "第二个", "时间": "昨晚9点"}
            ],
        }
    ]


@pytest.fixture
def multi_predictions():
    """Sample multi-label model output."""
    return [
        {"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]},
        {"category": "查看摄像头回放", "args": [{"设备类型": "摄像头", "时间": "昨天"}]},
    ]


@pytest.fixture
def fallback_predictions():
    """Sample fallback prediction."""
    return [{"category": "其他意图", "args": []}]


@pytest.fixture
def mock_api_response():
    """Mock OpenAI-style API response."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1791943333,
        "model": "Xing4.0-29B-A4B",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '[{"category": "查看摄像头回放", "args": [{"设备类型": "摄像头", "设备序号": "第二个", "时间": "昨晚9点"}]}]',
                },
                "finish_reason": "stop",
            }
        ],
    }
