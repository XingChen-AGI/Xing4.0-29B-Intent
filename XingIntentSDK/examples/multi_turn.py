"""Multi-turn dialog example for XingIntent SDK.

Demonstrates using Dialog builder for multi-turn conversations.
"""

from xingintent import Arg, Dialog, Intent, IntentClient


def main():
    client = IntentClient(
        base_url="http://localhost:8000/v1",
        model="your-model-name",
    )

    intents = [
        Intent(
            category="查看摄像头直播",
            description="用户想要实时查看摄像头等设备的当前实时画面。",
            args=[
                Arg("设备名称", "用户明确提及的设备名称或位置。"),
            ],
        ),
        Intent.fallback("其他意图"),
    ]

    dialog = (
        Dialog()
        .human("我想看看摄像头画面。")
        .ai("你想查看哪个房间？")
        .human("卧室。")
    )

    result = client.predict(dialog=dialog, intents=intents)

    print(f"Category: {result.category}")
    print(f"Args: {result.args}")

    dialog2 = Dialog.from_messages([
        {"role": "user", "content": "看看门口"},
        {"role": "assistant", "content": "您是想看直播还是回放？"},
        {"role": "user", "content": "直播"},
    ])

    result2 = client.predict(dialog=dialog2, intents=intents)
    print(f"\nCategory: {result2.category}")
    print(f"Args: {result2.args}")


if __name__ == "__main__":
    main()
