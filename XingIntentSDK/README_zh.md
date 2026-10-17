# XingIntent SDK

意图识别模型的配套 Python SDK。提供声明式的意图定义、自动化提示词拼装、多轮对话支持和结构化的结果访问，让调用方几行代码完成意图分类与参数抽取。

## 特性

- 声明式意图定义
- 自动提示词拼装，内部按模型规范完成 schema 序列化、模板替换、消息构造
- 多轮对话支持，链式 builder 自动渲染为 `Human: / AI:` 格式
- 富结果对象，属性访问无需手动解析 JSON
- 内置校验管线，自动过滤无效参数、校验类别合法性
- 支持 vLLM 约束解码（response_format），提升输出稳定性
- 同时提供同步和异步客户端
- 兼容 OpenAI 接口协议

## 安装

从源码安装：

```bash
cd XingIntentSDK
pip install -e .
```

## Quickstart

### 单轮推理

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

### 多轮对话

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

也可以从标准 messages 列表构建：

```python
dialog = Dialog.from_messages([
    {"role": "user", "content": "我想看看摄像头画面。"},
    {"role": "assistant", "content": "你想查看哪个房间？"},
    {"role": "user", "content": "卧室。"},
])

result = client.predict(dialog=dialog, intents=intents)
```

### 异步调用

推理是耗时操作，异步客户端不会阻塞事件循环，适合 Web 服务等异步场景：

```python
import asyncio
from xingintent import AsyncIntentClient, Intent, Arg

async def main():
    client = AsyncIntentClient(
        base_url="http://localhost:8000/v1",
        model="Xing4.0-29B-Intent",
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

### 从 JSON 文件加载 Schema

```python
from xingintent import IntentClient, Schema

schema = Schema.from_json("schema.json")

client = IntentClient(base_url="http://localhost:8000/v1", model="your-model-name")
result = client.predict(text="看看客厅摄像头", intents=schema)
```

schema.json 格式：

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

### 多标签场景

模型返回多个意图时，通过 `result.intents` 遍历。调用前需定义所有候选意图，包括示例中的“控制灯”：

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

`item.args` 是参数字典组成的列表。`result.category` 和 `result.args` 仅访问第一个意图，其中 `result.args` 会合并该意图的多组参数，同名字段以后出现的值为准。如需保留全部参数实例，请使用 `result.intents` 中各项的 `args`。

### 开启约束解码（response_format）

开启后 SDK 会根据意图定义自动生成 JSON Schema，通过 `response_format` 字段传给 vLLM，用约束解码确保输出格式始终合法：

```python
result = client.predict(
    text="我要看第二个摄像头昨晚9点的云回放",
    intents=intents,
    guided_json=True,
)
```

发送的请求会自动包含以下结构的 `response_format`。其中 `schema` 表示根据意图定义生成的完整 JSON Schema 字典：

```python
# 请求片段；schema 为 SDK 生成的 JSON Schema 字典。
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

### 鉴权配置

通过 `api_key` 参数设置 Bearer Token：

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    api_key="sk-your-key",
)
```

也可以传入自定义 headers 适配其他鉴权方式：

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    headers={"X-Api-Key": "your-token"},
)
```

两者可以同时使用。

### System Prompt 与模板配置

SDK 默认使用内置的 system prompt（星辰大模型身份声明）和 user prompt 模板。直接使用无需额外配置：

```python
client = IntentClient(base_url="http://localhost:8000/v1", model="your-model-name")
# 默认已包含 system prompt，无需手动设置
```

如需覆盖 system prompt：

```python
# 自定义 system
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    system_prompt="你是一个意图识别助手。",
)

# 完全去掉 system（回到纯 user 消息模式）
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    system_prompt="",
)
```

如需覆盖 user prompt 模板，模板中必须包含 `{intent_descriptions}` 和 `{user_input}` 两个占位符：

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    prompt_template=" Schema: {intent_descriptions}\nInput: {user_input}",
)
```

### 异常处理

SDK 对推理和解析过程中的异常做了完整的分类抛出：

```python
from xingintent import APIError, ParseError, ValidationError

try:
    result = client.predict(text="hello", intents=intents)
except APIError as e:
    print(f"模型服务异常: {e} (status={e.status_code})")
except ParseError as e:
    print(f"模型输出解析失败: {e}")
    print(f"原始输出: {e.raw_content}")
except ValidationError as e:
    print(f"结果校验失败: {e} (category={e.category})")
```

| 异常                | 触发场景                                                |
| ------------------- | ------------------------------------------------------- |
| `APIError`        | 网络错误、非 200 响应、响应 JSON 解码失败、choices 为空 |
| `ParseError`      | 模型输出无法解析为 JSON                                 |
| `ValidationError` | 预测的 category 不在 schema 中                          |
| `SchemaError`     | Schema 定义不合法                                       |
| `ValueError`      | 未提供 text/dialog 或同时提供了两者                     |

### Debug 模式

开启 debug 模式后，SDK 会输出内部处理流程的日志，包括 prompt 拼装、请求发送、响应解析、后处理等环节：

```python
client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="your-model-name",
    debug=True,
)

result = client.predict(text="看看客厅摄像头", intents=intents)
```

输出示例：

```
14:30:01 [DEBUG] xingintent: predict started | input_type=text, schema_categories=["查看摄像头直播", "查看摄像头回放", "其他意图"]
14:30:01 [DEBUG] xingintent: payload assembled | payload={"model": "your-model-name", "messages": [{"role": "user", "content": "### 任务说明\n\n根据【字段说明】判断...（完整 prompt 内容）..."}], "temperature": 0, "max_tokens": 128, "chat_template_kwargs": {"enable_thinking": false}}
14:30:01 [DEBUG] xingintent: sending request | url=http://localhost:8000/v1/chat/completions
14:30:02 [DEBUG] xingintent: response received | status_code=200, response_length=156
14:30:02 [DEBUG] xingintent: raw model output | content=[{"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]}]
14:30:02 [DEBUG] xingintent: parsed predictions | predictions=[{"category": "查看摄像头直播", "args": [{"设备名称": "客厅"}]}]
14:30:02 [DEBUG] xingintent: arg_validate applied | categories=["查看摄像头直播"], arg_count_before=1, arg_count_after=1
14:30:02 [DEBUG] xingintent: result built | category="查看摄像头直播", is_fallback=false, is_multi=false
```

`payload assembled` 行会输出完整的请求 body（包含 model、messages、temperature、max_tokens、chat_template_kwargs），可以直接复制用作调试对比。

也支持通过标准 logging 配置接管：

```python
import logging
logging.getLogger("xingintent").setLevel(logging.DEBUG)
```

## API 参考

### IntentClient / AsyncIntentClient

```python
IntentClient(
    base_url,           # 模型服务地址
    model,              # 模型名称
    api_key="",         # Bearer Token 鉴权
    headers=None,       # 自定义 HTTP headers
    max_tokens=128,     # 模型最大输出 token 数
    timeout=30.0,       # 请求超时（秒）
    postprocessors=None, # 后处理器列表，默认 ["arg_validate"]
    debug=False,         # 开启后输出内部处理流程日志
    system_prompt=None,  # None=内置默认 system，""=不发送 system，"自定义"=覆盖
    prompt_template=None, # 自定义 user prompt 模板，含 {intent_descriptions} 和 {user_input}
)

AsyncIntentClient(...)  # 参数相同
```

**方法：**

| 方法                                                                   | 说明             |
| ---------------------------------------------------------------------- | ---------------- |
| `client.predict(intents, text=None, dialog=None, guided_json=False)` | 执行意图识别     |
| `await async_client.predict(...)`                                    | 异步执行意图识别 |

`intents` 可以是 `list[Intent]` 或 `Schema`。`text` 和 `dialog` 二选一。

### Intent / Arg

```python
Intent(
    category,           # 意图名称
    description,        # 意图含义、判断条件、边界
    args=[]             # 参数列表
)

Arg(name, description)  # 参数名和描述

Intent.fallback("其他意图")  # 快捷创建兜底意图
```

### Schema

```python
Schema(intents)                   # 从 Intent 列表创建
Schema.from_json("schema.json")   # 从 JSON 文件加载
Schema.from_json(json_string)     # 从 JSON 字符串加载
schema.to_json()                  # 序列化为紧凑 JSON
```

### Dialog

```python
Dialog()                          # 创建空对话
Dialog().human("...").ai("...")   # 链式添加轮次
Dialog.from_messages(messages)    # 从 messages 列表创建
```

### PredictResult

| 属性 / 方法                     | 类型                   | 说明                 |
| ------------------------------- | ---------------------- | -------------------- |
| `result.category`             | `str`                | 首要意图名称         |
| `result.args`                 | `dict`               | 首要意图的参数键值对 |
| `result.get(key, default="")` | `str`                | 获取单个参数值       |
| `result.is_fallback`          | `bool`               | 是否命中兜底意图     |
| `result.is_multi`             | `bool`               | 是否多标签           |
| `result.intents`              | `list[IntentResult]` | 全部意图结果         |
| `result.raw`                  | `list`               | 原始解析后的 JSON    |
| `result[0]`                   | `IntentResult`       | 按索引访问           |
| `for item in result`          | —                     | 遍历所有意图         |

### IntentResult

| 属性 / 方法                   | 类型           | 说明               |
| ----------------------------- | -------------- | ------------------ |
| `item.category`             | `str`        | 意图名称           |
| `item.args`                 | `list[dict]` | 原始参数列表       |
| `item.args_flat`            | `dict`       | 合并后的参数键值对 |
| `item.get(key, default="")` | `str`        | 获取单个参数值     |
| `item["参数名"]`            | `str`        | 字典式访问         |

## 要求

- Python >= 3.8
- httpx >= 0.24

## License

采用 [Apache License 2.0](../LICENSE)，许可证统一位于仓库根目录。
