"""
XingIntent SDK — Intent recognition toolkit for XingIntent models.

Quick start::

    from xingintent import IntentClient, Intent, Arg, Dialog

    client = IntentClient(
        base_url="http://localhost:8000/v1",
        model="your-model-name",
    )

    intents = [
        Intent("查看摄像头直播", "用户想要实时查看摄像头画面...",
               args=[Arg("设备名称", "设备名称或位置")]),
        Intent.fallback("其他意图"),
    ]

    result = client.predict(text="看看客厅的摄像头", intents=intents)
    print(result.category)  # "查看摄像头直播"
    print(result.args)      # {"设备名称": "客厅"}
"""

from .client import AsyncIntentClient, IntentClient
from .dialog import Dialog
from .exceptions import (
    APIError,
    ParseError,
    PromptError,
    SchemaError,
    ValidationError,
    XingIntentError,
)
from .result import IntentResult, PredictResult
from .schema import Arg, Intent, Schema

__version__ = "0.1.0"

__all__ = [
    "APIError",
    "Arg",
    "AsyncIntentClient",
    "Dialog",
    "Intent",
    "IntentClient",
    "IntentResult",
    "ParseError",
    "PredictResult",
    "PromptError",
    "Schema",
    "SchemaError",
    "ValidationError",
    "XingIntentError",
]
