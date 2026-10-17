"""Prompt assembly for intent recognition.

Handles:
- System message with default identity prompt.
- Schema serialization to compact JSON (no indentation).
- Template substitution of {intent_descriptions} and {user_input}.
- Multi-turn dialog rendering.
- Message list construction (system + user).
"""

from typing import List, Optional, Union

from .dialog import Dialog
from .schema import Schema


DEFAULT_SYSTEM_PROMPT = (
    "你是中国电信星辰语义大模型，英文名是TeleChat，"
    "你是由中电信人工智能科技有限公司研发的人工智能助手。\n"
)

PROMPT_TEMPLATE = """### 任务说明

根据【字段说明】判断【输入内容】所属类别，并抽取该类别对应的参数。
category 和参数名必须来自字段说明，不得自行新增。
只填写输入中明确表达的参数；没有可填写参数时 args 为 []。
args 中每个对象表示一组相关参数实例，多组独立实例分别放在不同对象中。
如果输入涉及多个类别，以列表形式返回。
如果输入包含多轮对话，根据最后一轮用户输入判断，并结合对话历史抽取参数。
只输出有效 JSON 数组，不包含 Markdown 标记或额外说明。
输出结构：[{"category":"意图名称","args":[{"参数名":"参数值"}]}]

### 字段说明

{intent_descriptions}

### 输入内容

{user_input}"""


def build_prompt(
    schema: Schema,
    user_input: Union[str, Dialog],
    template: Optional[str] = None,
) -> str:
    """Assemble the full user prompt content.

    Args:
        schema: The intent schema defining candidate categories.
        user_input: Either a plain string (single-turn) or a Dialog (multi-turn).
        template: Optional custom prompt template. Must contain
            {intent_descriptions} and {user_input} placeholders.
            Defaults to the built-in PROMPT_TEMPLATE.

    Returns:
        The assembled prompt string to be placed in the user message content.
    """
    tmpl = template if template is not None else PROMPT_TEMPLATE

    # Step 1: Serialize schema to compact JSON text.
    schema_text = schema.to_json()

    # Step 2: Render user input.
    if isinstance(user_input, Dialog):
        input_text = user_input.render()
    else:
        input_text = str(user_input)

    # Step 3: Substitute placeholders.
    prompt = tmpl.replace("{intent_descriptions}", schema_text)
    prompt = prompt.replace("{user_input}", input_text)

    return prompt


def build_messages(
    schema: Schema,
    user_input: Union[str, Dialog],
    system_prompt: Optional[str] = None,
    template: Optional[str] = None,
) -> List[dict]:
    """Build the messages list for the chat completions API.

    Args:
        schema: The intent schema.
        user_input: Plain string or Dialog.
        system_prompt: System message content. Pass None to use the
            default identity prompt, or pass an empty string "" to
            omit the system message entirely.
        template: Optional custom prompt template.

    Returns:
        Message list with system (if present) and user messages.
    """
    content = build_prompt(schema, user_input, template=template)
    messages = []

    if system_prompt is None:
        messages.append({"role": "system", "content": DEFAULT_SYSTEM_PROMPT})
    elif system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": content})
    return messages
