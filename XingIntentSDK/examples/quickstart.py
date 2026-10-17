"""Quickstart example for XingIntent SDK.

Demonstrates single-turn intent prediction.
"""

from xingintent import Arg, Intent, IntentClient


def main():
    client = IntentClient(
        base_url="http://localhost:8000/v1",
        model="your-model-name",
    )

    intents = [
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
                        "典型表达：看第X个设备的录像/回放、看第X条录像、看昨天下午4点的云回看。",
            args=[
                Arg("设备类型", "摄像头、门铃、猫眼、视频锁等设备类型。"),
                Arg("位置", "设备所在位置，如卧室、客厅、门口。"),
                Arg("时间", "用户要查看的回放时间段，如今天9点、昨天下午4点。"),
                Arg("设备序号", "用户用'第X个+设备'指代设备时的序号。"),
                Arg("录像序号", "用户用'第X条+录像'指代录像时的序号。"),
            ],
        ),
        Intent.fallback("其他意图"),
    ]

    result = client.predict(text="我要看第二个摄像头昨晚9点的云回放", intents=intents)

    print(f"Category: {result.category}")
    print(f"Args: {result.args}")
    print(f"Is fallback: {result.is_fallback}")
    print(f"Time: {result.get('时间')}")


if __name__ == "__main__":
    main()
