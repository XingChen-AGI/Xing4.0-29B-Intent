"""Schema from JSON file example.

Shows loading intent definitions from a JSON file.
"""

import json

from xingintent import IntentClient, Schema


# Sample schema file content
SAMPLE_SCHEMA = [
    {
        "category": "查看摄像头直播",
        "category_description": "用户想要实时查看摄像头等设备的当前实时画面。",
        "args": [
            {"name": "设备名称", "description": "用户明确提及的设备名称或位置。"}
        ]
    },
    {
        "category": "查看摄像头回放",
        "category_description": "用户想要查看设备的回看或存储画面。",
        "args": [
            {"name": "设备类型", "description": "摄像头、门铃、猫眼、视频锁等。"},
            {"name": "时间", "description": "回放时间段。"}
        ]
    },
    {
        "category": "其他意图",
        "category_description": "用户输入无法匹配上述类别。",
        "args": []
    }
]


def main():
    # Write sample schema to file
    with open("camera_schema.json", "w", encoding="utf-8") as f:
        json.dump(SAMPLE_SCHEMA, f, ensure_ascii=False, indent=2)

    # Load schema from JSON file
    schema = Schema.from_json("camera_schema.json")

    print(f"Loaded {len(schema)} intents:")
    for intent in schema:
        print(f"  - {intent.category} ({len(intent.args)} args)")

    # Or from JSON string directly
    schema2 = Schema.from_json(json.dumps(SAMPLE_SCHEMA, ensure_ascii=False))

    # Use with client
    client = IntentClient(
        base_url="http://localhost:8000/v1",
        model="your-model-name",
    )

    result = client.predict(text="看看客厅摄像头", intents=schema)
    print(f"\nCategory: {result.category}")
    print(f"Args: {result.args}")


if __name__ == "__main__":
    main()
