# XingIntent SDK

[English](README.md) | [简体中文](README_zh.md)

A Python SDK for the intent recognition model. It provides declarative intent definitions, automatic prompt assembly, multi-turn conversation support, and structured result access, so callers can classify intents and extract arguments with a few lines of code.

## Features

- Declarative intent definitions.
- Automatic prompt assembly, including schema serialization, template substitution, and message construction according to the model's input format.
- Multi-turn conversations with a chainable builder that renders turns as `Human: / AI:`.
- Structured result objects with attribute access, without manual JSON parsing.
- A built-in validation pipeline that filters invalid arguments and checks category names.
- vLLM constrained decoding through `response_format` for more reliable output formatting.
- Synchronous and asynchronous clients.
- Compatibility with the OpenAI API protocol.

## Installation

Install from source:

```bash
cd XingIntentSDK
pip install -e .
```

## Quickstart

The examples below retain the Chinese input, schema labels, and expected results from the Chinese documentation. Replace `base_url` and `model` with your service address and served model name.

### Single-Turn Inference

```python
from xingintent import IntentClient, Intent, Arg

client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
)

intents = [
    Intent(
        category="查看摄像头直播",
        description="用户想要实时查看摄像头、门铃等设备的当前实时画面。",
        args=[
            Arg("设备名称", "用户提及的设备名称或位置，例如卧室、客厅")
        ],
    ),
    Intent(
        category="查看摄像头回放",
        description="用户想要查看设备的回看或存储画面。",
        args=[
            Arg("设备类型", "摄像头、门铃、猫眼、视频锁等"),
            Arg("位置", "设备所在位置，如卧室、客厅、门口"),
            Arg("时间", "回放时间段，如今天9点、昨天下午4点"),
            Arg("设备序号", "用户用'第X个+设备'指代设备时的序号"),
        ],
    ),
    Intent.fallback("其他意图"),
]

result = client.predict(text="我要看第二个摄像头昨晚9点的云回放", intents=intents)

print(result.category)        # "查看摄像头回放"
print(result.args)            # {"设备类型": "摄像头", "设备序号": "第二个", "时间": "昨晚9点"}
print(result.get("时间"))      # "昨晚9点"
print(result.is_fallback)     # False
```

### Multi-Turn Conversations

```python
from xingintent import IntentClient, Intent, Arg, Dialog

client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
)

intents = [
    Intent("查看摄像头直播", "实时查看摄像头画面",
           args=[Arg("设备名称", "设备名称或位置")]),
    Intent.fallback("其他意图"),
]

dialog = (
    Dialog()
    .human("我想看看摄像头画面。")
    .ai("你想查看哪个房间？")
    .human("卧室。")
)

result = client.predict(dialog=dialog, intents=intents)

print(result.category)   # "查看摄像头直播"
print(result.args)       # {"设备名称": "卧室"}
```

You can also build a dialog from a standard messages list:

```python
dialog = Dialog.from_messages([
    {"role": "user", "content": "我想看看摄像头画面。"},
    {"role": "assistant", "content": "你想查看哪个房间？"},
    {"role": "user", "content": "卧室。"},
])

result = client.predict(dialog=dialog, intents=intents)
```

### Asynchronous Calls

Inference can take time. The asynchronous client avoids blocking the event loop and is suitable for web services and other asynchronous applications:

```python
import asyncio
from xingintent import AsyncIntentClient, Intent, Arg

async def main():
    client = AsyncIntentClient(
        base_url="http://localhost:8000/v1",
        model="your-model-name",
    )

    intents = [
        Intent("查看摄像头直播", "实时查看摄像头画面",
               args=[Arg("设备名称", "设备名称或位置")]),
        Intent.fallback("其他意图"),
    ]

    result = await client.predict(text="看看客厅摄像头", intents=intents)
    print(result.category)   # "查看摄像头直播"
    print(result.args)       # {"设备名称": "客厅"}

asyncio.run(main())
```

### Load a Schema from JSON

```python
from xingintent import IntentClient, Schema

schema = Schema.from_json("schema.json")

client = IntentClient(base_url="http://localhost:8000/v1", model="your-model-name")
result = client.predict(text="看看客厅摄像头", intents=schema)
```

The format of `schema.json`:

```json
[
  {
    "category": "查看摄像头直播",
    "category_description": "用户想要实时查看摄像头画面。",
    "args": [{"name": "设备名称", "description": "设备名称或位置"}]
  },
  {
    "category": "其他意图",
    "category_description": "用户输入无法匹配上述类别。",
    "args": []
  }
]
```

### Multi-Label Predictions

When the model returns multiple intents, iterate over `result.intents`. Define all candidate intents, including light control, before making this request:

```python
intents = [
    Intent("控制灯", "打开或关闭灯", args=[Arg("开关", "开或关")]),
    Intent("查看摄像头直播", "实时查看摄像头画面",
           args=[Arg("设备名称", "设备名称或位置")]),
    Intent(
        "查看摄像头回放",
        "查看摄像头的历史录像或云回放",
        args=[
            Arg("设备类型", "摄像头、门铃、猫眼、视频锁等"),
            Arg("位置", "设备所在位置，如卧室、客厅、门口"),
            Arg("时间", "回放时间段，如昨晚9点"),
            Arg("设备序号", "用户用第X个设备指代设备时的序号"),
        ],
    ),
    Intent.fallback("其他意图"),
]

result = client.predict(text="帮我开灯顺便看看客厅摄像头", intents=intents)
print(result.is_multi)    # True

for item in result.intents:
    print(item.category, item.args)
# 控制灯 [{'开关': '开'}]
# 查看摄像头直播 [{'设备名称': '客厅'}]
```

Each `item.args` is a list of argument dictionaries. The convenience properties `result.category` and `result.args` refer to the first intent only. `result.args` merges that intent's argument instances; later values overwrite earlier ones for duplicate keys. Use `result.intents` and each item's `args` to preserve all instances.

### Enable Constrained Decoding (`response_format`)

When enabled, the SDK generates a JSON Schema from the intent definitions and sends it to vLLM through `response_format`. A server with support for JSON Schema constrained decoding uses this schema to constrain the output format:

```python
result = client.predict(
    text="我要看第二个摄像头昨晚9点的云回放",
    intents=intents,
    guided_json=True,
)
```

The request includes a `response_format` object with this structure. Here, `schema` represents the full JSON Schema generated from your intent definitions:

```python
# Request fragment; schema is the generated JSON Schema dictionary.
{
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "intent_result",
            "schema": schema,
        },
    },
}
```

### Authentication

Set a Bearer token with `api_key`:

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    api_key="sk-your-key",
)
```

Use custom headers for other authentication schemes:

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    headers={"X-Api-Key": "your-token"},
)
```

Both options can be used together.

### System Prompt and Template Configuration

The SDK uses a built-in system prompt identifying the Xing model and a default user prompt template. No additional configuration is required:

```python
client = IntentClient(base_url="http://localhost:8000/v1", model="your-model-name")
# The default system prompt is already included.
```

To override or omit the system prompt:

```python
# Custom system prompt
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    system_prompt="你是一个意图识别助手。",
)

# Omit the system message and send only the user message
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    system_prompt="",
)
```

To override the user prompt template, include both `{intent_descriptions}` and `{user_input}` placeholders:

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    prompt_template=" Schema: {intent_descriptions}\nInput: {user_input}",
)
```

### Error Handling

The SDK exposes separate exception types for service, parsing, and validation errors:

```python
from xingintent import APIError, ParseError, ValidationError

try:
    result = client.predict(text="hello", intents=intents)
except APIError as e:
    print(f"Model service error: {e} (status={e.status_code})")
except ParseError as e:
    print(f"Failed to parse model output: {e}")
    print(f"Raw output: {e.raw_content}")
except ValidationError as e:
    print(f"Result validation failed: {e} (category={e.category})")
```

| Exception | When it occurs |
| --- | --- |
| `APIError` | Network errors, non-200 responses, response JSON decoding failures, or empty `choices` |
| `ParseError` | Model output cannot be parsed as JSON |
| `ValidationError` | A predicted category is not in the schema |
| `SchemaError` | An invalid schema definition |
| `ValueError` | Neither `text` nor `dialog` is provided, or both are provided |

### Debug Mode

Enable debug mode to log internal processing steps, including prompt assembly, request sending, response parsing, and postprocessing:

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    debug=True,
)

result = client.predict(text="看看客厅摄像头", intents=intents)
```

Example log excerpt (payload abbreviated):

```text
14:30:01 [DEBUG] xingintent: predict started | input_type=text, schema_categories=["查看摄像头直播", "查看摄像头回放", "其他意图"]
14:30:01 [DEBUG] xingintent: payload assembled | payload={...}
14:30:01 [DEBUG] xingintent: sending request | url=http://localhost:8000/v1/chat/completions
14:30:02 [DEBUG] xingintent: response received | status_code=200, response_length=156
14:30:02 [DEBUG] xingintent: raw model output | content=[{"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]}]
14:30:02 [DEBUG] xingintent: parsed predictions | predictions=[{"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]}]
14:30:02 [DEBUG] xingintent: arg_validate applied | categories=["查看摄像头直播"], arg_count_before=1, arg_count_after=1
14:30:02 [DEBUG] xingintent: result built | category="查看摄像头直播", is_fallback=false, is_multi=false
```

The actual `payload assembled` log entry contains the complete request body, including `model`, `messages`, `temperature`, `max_tokens`, and `chat_template_kwargs`, which can be used to compare requests while debugging.

You can also configure the SDK logger through Python's standard logging module:

```python
import logging
logging.getLogger("xingintent").setLevel(logging.DEBUG)
```

## API Reference

### IntentClient / AsyncIntentClient

```python
IntentClient(
    base_url,           # Model service URL
    model,              # Served model name
    api_key="",         # Bearer token authentication
    headers=None,       # Custom HTTP headers
    max_tokens=128,     # Maximum output tokens
    timeout=30.0,       # Request timeout in seconds
    postprocessors=None, # Postprocessors; defaults to ["arg_validate"]
    debug=False,         # Log internal processing steps when enabled
    system_prompt=None,  # None: built-in default; "": omit; other strings: override
    prompt_template=None, # Custom user template containing {intent_descriptions} and {user_input}
)

AsyncIntentClient(...)  # Same parameters
```

**Methods:**

| Method | Description |
| --- | --- |
| `client.predict(intents, text=None, dialog=None, guided_json=False)` | Run intent recognition |
| `await async_client.predict(...)` | Run intent recognition asynchronously |

`intents` accepts a list of `Intent` objects or a `Schema`. Provide exactly one of `text` and `dialog`.

### Intent / Arg

```python
Intent(
    category,           # Intent name
    description,        # Intent meaning, decision criteria, and boundaries
    args=[]             # Argument list
)

Arg(name, description)  # Argument name and description

Intent.fallback("其他意图")  # Create a fallback intent
```

### Schema

```python
Schema(intents)                   # Create from a list of Intent objects
Schema.from_json("schema.json")   # Load from a JSON file
Schema.from_json(json_string)     # Load from a JSON string
schema.to_json()                  # Serialize to compact JSON
```

### Dialog

```python
Dialog()                          # Create an empty dialog
Dialog().human("...").ai("...")   # Append turns using chained calls
Dialog.from_messages(messages)    # Create from a messages list
```

### PredictResult

| Property / method | Type | Description |
| --- | --- | --- |
| `result.category` | `str` | First predicted intent name |
| `result.args` | `dict` | Merged argument dictionary for the first intent |
| `result.get(key, default="")` | `str` | Get an argument value from the first intent |
| `result.is_fallback` | `bool` | Whether the first intent matches the configured fallback |
| `result.is_multi` | `bool` | Whether multiple intents were returned |
| `result.intents` | `list[IntentResult]` | All intent results |
| `result.raw` | `list` | Parsed JSON result list |
| `result[0]` | `IntentResult` | Access an intent by index |
| `for item in result` | — | Iterate over all intents |

### IntentResult

| Property / method | Type | Description |
| --- | --- | --- |
| `item.category` | `str` | Intent name |
| `item.args` | `list[dict]` | Argument instances as a list |
| `item.args_flat` | `dict` | Merged argument dictionary; later values overwrite earlier ones for duplicate keys |
| `item.get(key, default="")` | `str` | Get an argument value from the merged dictionary |
| `item["参数名"]` | `str` | Dictionary-style access by argument name |

## Requirements

- Python >= 3.8
- httpx >= 0.24

## License

Released under the [Apache License 2.0](../LICENSE). The license file is located at the repository root.
