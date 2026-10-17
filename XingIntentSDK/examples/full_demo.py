"""
XingIntent SDK 完整功能覆盖示例。

使用前修改下方配置，直接运行：
    python examples/full_demo.py

覆盖功能：
  1. 同步单轮推理
  2. 同步多轮推理（Dialog 链式 + from_messages）
  3. 异步推理
  4. guided_json 约束解码
  5. 从 JSON 文件加载 Schema
  6. 多标签场景
  7. 兜底意图检测
  8. debug 模式
  9. 异常处理（APIError / ParseError / ValidationError）
"""

import asyncio
import json
import os
import tempfile
import time

from xingintent import (
    APIError,
    Arg,
    AsyncIntentClient,
    Dialog,
    Intent,
    IntentClient,
    ParseError,
    Schema,
    ValidationError,
)

# ============================================================
# 配置区 —— 改成你的真实配置
# ============================================================
BASE_URL = "http://localhost:8000/v1"
MODEL = "your-model-name"
API_KEY = ""  # 没有就留空
# ============================================================


def build_intents():
    """构造意图定义。"""
    return [
        Intent(
            category="查看摄像头直播",
            description="用户想要实时查看摄像头、门铃、猫眼、视频锁等设备的当前实时画面，"
                        "区别于查看历史存储的回放画面。"
                        "典型表达：看直播、看实时画面、看看现在/当前、看客厅的实时监控；"
                        "用户未提及过去时间的查看监控请求属于此类。",
            args=[
                Arg("设备名称", "用户明确提及的设备名称或位置，例如卧室、客厅；未提及时不填写。"),
            ],
        ),
        Intent(
            category="查看摄像头回放",
            description="用户想要查看设备的回看或存储画面，包括回放、录像、云回看、监控回看等表达。"
                        "典型表达：看第X个设备的录像/回放、看第X条录像、看昨天下午4点的云回看；"
                        "用户用'第X个+设备'或'第X条+录像'指代具体设备或录像时，均属于本意图。",
            args=[
                Arg("设备类型", "摄像头、门铃、猫眼、视频锁等设备类型。"),
                Arg("位置", "用户提及的设备所在位置，如卧室、客厅、门口。"),
                Arg("时间", "用户要查看的回放时间段，如今天9点、昨天下午4点。"),
                Arg("设备序号", "用户用'第X个+设备'指代设备时的序号。"),
                Arg("录像序号", "用户用'第X条+录像'指代录像时的序号，不得与设备序号混淆。"),
            ],
        ),
        Intent(
            category="控制设备",
            description="用户想要控制智能家居设备，如开关灯、调节温度、开关空调等。",
            args=[
                Arg("设备名称", "用户要控制的设备名称，如灯、空调、窗帘。"),
                Arg("操作", "用户要执行的操作，如开、关、调高、调低。"),
            ],
        ),
        Intent.fallback("其他意图"),
    ]


def make_client(debug=False):
    """创建同步客户端。"""
    return IntentClient(
        base_url=BASE_URL,
        model=MODEL,
        api_key=API_KEY,
        debug=debug,
    )


def make_async_client(debug=False):
    """创建异步客户端。"""
    return AsyncIntentClient(
        base_url=BASE_URL,
        model=MODEL,
        api_key=API_KEY,
        debug=debug,
    )


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ============================================================
# 1. 同步单轮推理
# ============================================================
def demo_sync_single_turn():
    section("1. 同步单轮推理")
    client = make_client()
    intents = build_intents()

    result = client.predict(text="我要看第二个摄像头昨晚9点的云回放", intents=intents)

    print("输入: 我要看第二个摄像头昨晚9点的云回放")
    print(f"意图: {result.category}")
    print(f"参数: {result.args}")
    print(f"兜底: {result.is_fallback}")
    print(f"多标签: {result.is_multi}")


# ============================================================
# 2. 同步多轮推理
# ============================================================
def demo_sync_multi_turn():
    section("2. 同步多轮推理")
    client = make_client()
    intents = build_intents()

    # 方式 A: Dialog 链式
    dialog = (
        Dialog()
        .human("我想看看摄像头画面。")
        .ai("你想查看哪个房间？")
        .human("卧室。")
    )
    result = client.predict(dialog=dialog, intents=intents)
    print("方式A - Dialog 链式:")
    print(f"  对话: {dialog.render()}")
    print(f"  意图: {result.category}")
    print(f"  参数: {result.args}")

    # 方式 B: from_messages
    dialog2 = Dialog.from_messages([
        {"role": "user", "content": "看看门口"},
        {"role": "assistant", "content": "您是想看直播还是回放？"},
        {"role": "user", "content": "直播"},
    ])
    result2 = client.predict(dialog=dialog2, intents=intents)
    print("\n方式B - from_messages:")
    print(f"  对话: {dialog2.render()}")
    print(f"  意图: {result2.category}")
    print(f"  参数: {result2.args}")


# ============================================================
# 3. 异步推理
# ============================================================
def demo_async():
    section("3. 异步推理")
    client = make_async_client()
    intents = build_intents()

    result = asyncio.run(
        client.predict(text="帮我打开客厅的灯", intents=intents)
    )

    print("输入: 帮我打开客厅的灯")
    print(f"意图: {result.category}")
    print(f"参数: {result.args}")


# ============================================================
# 4. guided_json 约束解码
# ============================================================
def demo_guided_json():
    section("4. guided_json 约束解码")
    client = make_client()
    intents = build_intents()

    result = client.predict(
        text="看看昨天下午3点客厅摄像头的回放",
        intents=intents,
        guided_json=True,
    )

    print("guided_json=True")
    print("输入: 看看昨天下午3点客厅摄像头的回放")
    print(f"意图: {result.category}")
    print(f"参数: {result.args}")


# ============================================================
# 5. 从 JSON 文件加载 Schema
# ============================================================
def demo_schema_from_json():
    section("5. 从 JSON 文件加载 Schema")
    intents = build_intents()
    schema_data = [i.to_dict() for i in intents]

    # 写到临时文件
    tmp = os.path.join(tempfile.gettempdir(), "xingintent_demo_schema.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(schema_data, f, ensure_ascii=False, indent=2)

    print(f"Schema 文件: {tmp}")

    # 从文件加载
    schema = Schema.from_json(tmp)
    print(f"加载了 {len(schema)} 个意图:")
    for intent in schema:
        print(f"  - {intent.category} (args: {len(intent.args)})")

    # 用加载的 schema 推理
    client = make_client()
    result = client.predict(text="看直播", intents=schema)
    print("\n输入: 看直播")
    print(f"意图: {result.category}")
    print(f"参数: {result.args}")

    # 也可以从 JSON 字符串加载
    schema2 = Schema.from_json(json.dumps(schema_data, ensure_ascii=False))
    assert len(schema2) == len(schema)
    print(f"\n从 JSON 字符串加载: {len(schema2)} 个意图 (OK)")


# ============================================================
# 6. 多标签场景
# ============================================================
def demo_multi_label():
    section("6. 多标签场景")
    client = make_client()
    intents = build_intents()

    result = client.predict(text="帮我打开客厅的灯顺便看看摄像头", intents=intents)

    print("输入: 帮我打开客厅的灯顺便看看摄像头")
    print(f"是否多标签: {result.is_multi}")
    if result.is_multi:
        for i, item in enumerate(result.intents):
            print(f"  [{i}] {item.category} -> {item.args_flat}")
    else:
        print(f"  仅检测到: {result.category}")


# ============================================================
# 7. 兜底意图检测
# ============================================================
def demo_fallback():
    section("7. 兜底意图检测")
    client = make_client()
    intents = build_intents()

    result = client.predict(text="今天天气怎么样", intents=intents)

    print("输入: 今天天气怎么样")
    print(f"意图: {result.category}")
    print(f"是否兜底: {result.is_fallback}")


# ============================================================
# 8. debug 模式
# ============================================================
def demo_debug():
    section("8. debug 模式")
    client = make_client(debug=True)
    intents = build_intents()

    print("（观察下方完整内部处理流程日志）\n")
    result = client.predict(text="看卧室摄像头的直播", intents=intents)

    print(f"\n意图: {result.category}")
    print(f"参数: {result.args}")


# ============================================================
# 9. 异常处理
# ============================================================
def demo_error_handling():
    section("9. 异常处理")

    intents = build_intents()

    # 9a. API 错误（指向一个不存在的服务）
    print("--- 9a. API 连接错误 ---")
    bad_client = IntentClient(
        base_url="http://127.0.0.1:19999/v1",
        model=MODEL,
        timeout=5,
    )
    try:
        bad_client.predict(text="test", intents=intents)
    except APIError as e:
        print(f"捕获 APIError: {e}")
        print(f"  status_code: {e.status_code}")

    # 9b. 正常推理的异常保护
    print("\n--- 9b. 完整异常处理模板 ---")
    client = make_client()
    try:
        result = client.predict(text="看摄像头", intents=intents)
        print(f"成功: {result.category}")
    except APIError as e:
        print(f"模型服务异常: {e} (status={e.status_code})")
    except ParseError as e:
        print(f"输出解析失败: {e}")
        print(f"原始输出: {e.raw_content}")
    except ValidationError as e:
        print(f"结果校验失败: {e} (category={e.category})")

    # 9c. 参数校验
    print("\n--- 9c. ValueError（未提供输入）---")
    try:
        client.predict(intents=intents)
    except ValueError as e:
        print(f"捕获 ValueError: {e}")


# ============================================================
# 结果对象 API 速览
# ============================================================
def demo_result_api():
    section("附: 结果对象 API 速览")
    client = make_client()
    intents = build_intents()

    result = client.predict(text="看第二个摄像头昨天9点的回放", intents=intents)

    print(f"result.category       = {result.category!r}")
    print(f"result.args           = {result.args!r}")
    print(f"result.get('时间')     = {result.get('时间')!r}")
    print(f"result.get('不存在', '默认值') = {result.get('不存在', '默认值')!r}")
    print(f"result.is_fallback    = {result.is_fallback}")
    print(f"result.is_multi       = {result.is_multi}")
    print(f"result.raw            = {result.raw!r}")
    print(f"len(result)           = {len(result)}")
    if result.intents:
        item = result.intents[0]
        print(f"result.intents[0].category   = {item.category!r}")
        print(f"result.intents[0].args_flat  = {item.args_flat!r}")
        print(f"result.intents[0].get('时间') = {item.get('时间')!r}")
        print(f"'时间' in item         = {'时间' in item}")
        print(f"item['时间']          = {item['时间']!r}")


# ============================================================
# 主函数
# ============================================================
def main():
    demos = [
        demo_sync_single_turn,
        demo_sync_multi_turn,
        demo_async,
        demo_guided_json,
        demo_schema_from_json,
        demo_multi_label,
        demo_fallback,
        demo_debug,
        demo_error_handling,
        demo_result_api,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:  # noqa: BLE001 - demo 脚本兜底，保证后续 demo 不中断
            print(f"[跳过] {demo.__name__} 失败: {e}")
        time.sleep(1)

    print(f"\n{'='*60}")
    print("  全部演示完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
