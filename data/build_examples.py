#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build examples from a schema-driven dataset directory.

Expected input layout:
    <root>/schema_description/<name>_schema.json
    <root>/dataset/<name>_dataset.json     # each item has a `dialogs` list
    <root>/prompt/<name>_prompt.json       # optional, built from schema if missing

Per-item fields:
    system       : optional system message; omitted when absent
    schema       : embedded schema (list) -- takes priority over schema_path
    schema_path  : path to a schema file, relative to --root
    prompt       : embedded prompt template (str) -- takes priority over default
    prompt_path  : path to a prompt file, relative to --root
    dialogs      : [{"role": "user"|"assistant", "content": "..."}]
    output       : expected answer, copied to the example as-is
    id/turn/task/source/domain/language : metadata, copied as-is

Assembly rules:
    system = optional, taken verbatim from the item's `system` field;
             no system message is emitted when the field is absent or empty
    user   = task prompt template (prompt file > embedded prompt > default)
             -> `{intent_descriptions}` replaced by the rendered schema
             -> output format rules inserted right before `{user_input}`
                (omitted with --no_format_rules)
             -> `{user_input}` replaced by the rendered dialogs;
                if the placeholder is absent, dialogs are appended at the end
    Each output line = id/turn/task/source/domain/language/messages/output/prompt_length

Usage (run from the model repository root containing data/ and XingIntentSDK/):
    # One dataset file
    python3 data/build_examples.py \
        --root /path/to/data_root \
        --dataset my_dataset.json \
        --save_path out/my_examples.jsonl

    # All dataset files under dataset/, one output file per dataset
    python3 data/build_examples.py --root /path/to/data_root --save_path out/

    # Pretty-printed JSON array instead of JSONL
    python3 data/build_examples.py --root /path/to/data_root --dataset my_dataset.json \
        --save_path out/my_examples.json --fmt json
"""
import os
import argparse
import json
import copy
import glob

# ======================= Constants =======================
# Unified placeholder for schema text inside a prompt template
SCHEMA_PLACEHOLDER = "{intent_descriptions}"

# Placeholder for the rendered dialogs inside a prompt template;
# if absent, the rendered dialogs are simply appended after the template
USER_INPUT_PLACEHOLDER = "{user_input}"

# Default task prompt template, used when neither a prompt file nor an
# embedded prompt is available; `{intent_descriptions}` and `{user_input}`
# are replaced at build time
DEFAULT_TASK_PROMPT = (
    "### 角色定义\n"
    "你是一个强大的信息抽取助手，具备意图理解、命名实体识别（NER）、关系抽取（RE）以及事件抽取（EE）等能力。\n"
    "你可以处理普通文本、单轮输入或多轮对话，并准确提取任务所需信息。\n\n"
    "### 任务描述\n"
    "请根据给定的【字段说明】选择与【输入内容】最匹配的类别，并按照字段格式抽取对应内容。\n"
    "输出结果以标准 JSON 格式返回。请确保只输出有效 JSON，不包含多余说明。\n"
    "如果【输入内容】以对话形式给出请根据最后一轮的用户输入进行字段类别判定，并结合对话历史进行字段内容抽取。\n"
    "如果最后一轮对话涉及多个类别请以列表形式返回。\n\n"
    "### 字段说明\n"
    "{intent_descriptions}\n\n"
    "### 输入内容\n"
    "{user_input}"
)

# Role mapping from dataset dialogs to rendered display names
ROLE_MAP = {
    "user": "Human",
    "assistant": "AI",
}

# Output format constraints, inserted after the task template and before the
# rendered dialogs
OUTPUT_FORMAT_RULES = """
### 输出格式规则
1、无论匹配单个还是多个类别，输出一律为 JSON 列表，如 [{"category": "xxx", "args": []}]；
2、args 内元素为键值对：键为【字段说明】中该类别槽位的 name 值（原样使用，禁止改写），值为从【输入内容】中抽取的该槽位实际内容；
3、该类别无槽位时 args 为空数组 []；禁止输出 name、description 字段，禁止输出 JSON 以外的任何文字。
"""


# ======================= Loading =======================
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_path(root, rel_path):
    """Resolve a per-item relative path (may start with './') to an absolute one."""
    return os.path.normpath(os.path.join(root, (rel_path or '').replace('./', '', 1)))


def render_schema_descriptions(schema):
    """Serialize a schema into JSON text for the schema placeholder."""
    return json.dumps(schema, ensure_ascii=False)


def load_prompt_system(root, entry):
    """
    Return the task prompt template for this entry, or None to use the default.
    Priority: prompt file > embedded prompt field > default template.
    """
    prompt_path = entry.get('prompt_path', '') or ''
    prompt_emb = entry.get('prompt', '') or ''
    if prompt_path:
        p = resolve_path(root, prompt_path)
        if os.path.exists(p):
            pf = load_json(p)
            return pf.get('system', '') if isinstance(pf, dict) else str(pf)
    if prompt_emb:
        return prompt_emb if isinstance(prompt_emb, str) else json.dumps(prompt_emb, ensure_ascii=False)
    return None


def load_schema(root, entry, schema_cache):
    """
    Resolve the schema for an entry.
    Embedded schema (list) first, otherwise load via schema_path (cached by path).
    """
    emb_schema = entry.get('schema')
    if isinstance(emb_schema, list) and emb_schema:
        return emb_schema
    schema_path = entry.get('schema_path', '') or ''
    sp = resolve_path(root, schema_path) if schema_path else ''
    if sp and os.path.exists(sp):
        schema = schema_cache.get(sp)
        if schema is None:
            schema = load_json(sp)
            schema_cache[sp] = schema
        return schema
    raise FileNotFoundError(f"invalid schema_path: {schema_path!r} (id={entry.get('id')})")


def render_dialogs(entry):
    """
    Render the dialogs list into multi-line text,
    with every turn prefixed by its mapped display name.
    """
    dialogs = entry.get('dialogs') or []
    if not dialogs:
        raise ValueError(f"item {entry.get('id')} has no dialogs")
    lines = []
    for d in dialogs:
        role_name = ROLE_MAP.get(d.get('role', ''), d.get('role', ''))
        lines.append(f"{role_name}: {d.get('content', '')}")
    return '\n'.join(lines)


# ======================= Assembly =======================
def build_messages(root, entry, schema_cache, with_format_rules=True):
    """
    Build the messages for one dataset entry.
    system is optional: taken from the item's `system` field, emitted only
    when present and non-empty; otherwise the messages contain user only.
    Returns (messages, schema).
    """
    # 1) schema
    schema = load_schema(root, entry, schema_cache)

    # 2) task prompt template: prompt file > embedded prompt > default
    task_prompt = load_prompt_system(root, entry)
    if task_prompt is None:
        task_prompt = DEFAULT_TASK_PROMPT

    # 3) render the schema into the template
    if SCHEMA_PLACEHOLDER in task_prompt:
        task_prompt = task_prompt.replace(SCHEMA_PLACEHOLDER, render_schema_descriptions(schema))
    # Insert format rules right before the user-input placeholder; when the
    # template has no such placeholder, append the rules at the end.
    # (Both cases keep the rules ahead of the dialog content.)
    has_format_rules = any(
        heading in task_prompt
        for heading in ('### 输出格式规则', '### Output Format')
    )
    if with_format_rules and not has_format_rules:
        rules = OUTPUT_FORMAT_RULES.strip('\n')
        if USER_INPUT_PLACEHOLDER in task_prompt:
            task_prompt = task_prompt.replace(
                USER_INPUT_PLACEHOLDER, rules + '\n\n' + USER_INPUT_PLACEHOLDER, 1)
        else:
            task_prompt = task_prompt.rstrip('\n') + '\n\n' + rules

    # 4) render dialogs
    dialog_text = render_dialogs(entry)

    # 5) assemble user content: replace the placeholder in place when present,
    #    otherwise append the dialogs after the template (no injected heading)
    if USER_INPUT_PLACEHOLDER in task_prompt:
        user_content = task_prompt.replace(USER_INPUT_PLACEHOLDER, dialog_text)
    else:
        user_content = task_prompt.rstrip('\n') + '\n' + dialog_text

    # 6) assemble messages: optional system (from the item's `system` field)
    #    followed by the user content; nothing is injected by default
    messages = []
    system_content = entry.get('system', '') or ''
    if isinstance(system_content, str) and system_content.strip():
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": user_content})
    return messages, schema


def build_example(root, entry, schema_cache, with_format_rules=True):
    """
    Build one full example (messages plus metadata).
    Returns None on failure and prints the error without aborting the batch.
    """
    try:
        entry = copy.deepcopy(entry)  # never mutate the source dataset
        messages, _ = build_messages(root, entry, schema_cache,
                                     with_format_rules=with_format_rules)
    except Exception as e:
        print(f"[build failed] id={entry.get('id')}: {type(e).__name__}: {e}")
        return None
    rec = {
        'id': entry.get('id'),
        'turn': entry.get('turn'),
        'task': entry.get('task'),
        'source': entry.get('source'),
        'domain': entry.get('domain'),
        'language': entry.get('language'),
        'messages': messages,
        'output': entry.get('output'),
        'prompt_length': sum(len(m['content']) for m in messages),
    }
    return rec


# ======================= Output =======================
def save_jsonl(items, save_path):
    out_dir = os.path.dirname(os.path.abspath(save_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        for r in items:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def save_json(items, save_path):
    out_dir = os.path.dirname(os.path.abspath(save_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def build_output_path(save_path, files, name):
    """
    Decide the output file path:
    - explicit filename with an extension -> use it as-is
    - directory or empty -> generate <stem>_examples.jsonl inside it
    """
    stem = os.path.splitext(name)[0]
    if save_path and len(files) == 1 and os.path.splitext(save_path)[1]:
        return save_path.rstrip('/')
    base = (save_path.rstrip('/') if save_path else '') or 'examples'
    return os.path.join(base, f'{stem}_examples.jsonl')


def main():
    parser = argparse.ArgumentParser(description="Build examples from a schema-driven dataset directory")
    parser.add_argument('--root', required=True,
                        help='data root directory (contains dataset/, schema_description/, prompt/)')
    parser.add_argument('--dataset', default=None,
                        help='process only this dataset file; otherwise all files under dataset/')
    parser.add_argument('--save_path', default=None,
                        help='output path: .jsonl (default) or .json with --fmt json; '
                             'treated as a directory when processing multiple files')
    parser.add_argument('--fmt', choices=['jsonl', 'json'], default='jsonl',
                        help='output format: jsonl (one per line, default) or json (indented array)')
    parser.add_argument('--max_samples', type=int, default=None,
                        help='keep at most the first N items per dataset')
    parser.add_argument('--no_format_rules', action='store_true',
                        help='do not insert the output format rules section')
    args = parser.parse_args()

    ds_root = os.path.join(args.root, 'dataset')
    if args.dataset:
        files = [os.path.join(ds_root, args.dataset)]
    else:
        files = sorted(glob.glob(os.path.join(ds_root, '*.json')))
    if not files:
        raise SystemExit(f"no dataset file found: {ds_root}")

    total_ok, total_fail = 0, 0
    for dpath in files:
        data = load_json(dpath)
        if not isinstance(data, list):
            data = [data]
        if args.max_samples:
            data = data[:args.max_samples]
        name = os.path.basename(dpath)
        print(f"\n>>> processing {name}: {len(data)} items")

        schema_cache = {}
        examples = []
        for entry in data:
            rec = build_example(args.root, entry, schema_cache,
                                with_format_rules=not args.no_format_rules)
            if rec is None:
                total_fail += 1
            else:
                examples.append(rec)
        total_ok += len(examples)

        out = build_output_path(args.save_path, files, name)
        if args.fmt == 'json':
            if not out.endswith('.json'):
                out = os.path.splitext(out)[0] + '.json'
            save_json(examples, out)
        else:
            save_jsonl(examples, out)
        print(f"written: {out} ({len(examples)} items)")

    print(f"\ndone: {total_ok} built, {total_fail} failed")


if __name__ == '__main__':
    main()
