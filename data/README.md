<h1 align="center">Xing4.0-29B-Intent-oss</h1>

<div align="center">

[English](./README.md) | [简体中文](./README_zh.md)

</div>

This dataset accompanies [Xing4.0-29B-Intent](../README.md), a model for intent recognition and structured information extraction. It is curated and released by the Xingchen General Artificial Intelligence Laboratory of China Telecom Artificial Intelligence Technology Co., Ltd. The dataset is referred to below as **Xing4.0-29B-Intent-oss**.

Given a caller-provided set of candidate categories (a schema), Xing4.0-29B-Intent performs **category classification and argument extraction in a single inference pass**, producing structured results that business systems can consume directly. The model is trained using two types of data:

- **Reconstructed public datasets**: 61 open-source information extraction and spoken language understanding datasets converted into a unified, schema-guided representation covering NER, RE, EE, and SLU, as described below.
- **China Telecom in-house domain data (smart-device assistant scenarios)**: intent and slot annotations collected for smart-device assistant use cases.

These data train the model to interpret categories and extract fields according to a schema. New use cases can be adapted by defining schemas and providing examples; performance must be validated on the target business data.

## What the Data Can Be Used For

- **Model training (SFT)**: construct training examples from `messages` + `output` to train chat-format models to produce structured outputs across the four task types.
- **Model evaluation**: evaluate schema-guided semantic understanding across intent recognition and slot filling, named entity recognition, relation extraction, and event extraction. Reproducing a specific evaluation result also requires matching data versions, evaluation scripts, and inference settings.
- **Cold-start testing**: assess generalization to unseen schemas across tasks, domains, and languages, and evaluate the effort required to adapt to new use cases through configuration changes.
- **Prompt and format research**: all tasks share a “task instructions + schema + input” prompt assembly protocol, enabling comparisons of how schema wording and category granularity affect extraction results.

## Directory Structure

```text
data/
├── General/                      # Reconstructed public datasets, organized by split
│   ├── train/
│   │   ├── dataset/              # Samples named by dataset, e.g. MTOP.json
│   │   ├── schema_description/   # Corresponding category definitions
│   │   └── prompt/               # Optional task-specific prompt templates
│   ├── dev/                      # Same structure as train/
│   └── test/                     # Same structure as train/
├── XingChen/                     # In-house smart-device assistant data
│   ├── dataset/
│   ├── schema_description/
│   └── prompt/
└── build_examples.py             # Example assembly script
```

- `General/<split>/` and `XingChen/` share the same organization: `dataset/`, `schema_description/`, and an optional `prompt/` directory. `build_examples.py` processes both in the same way.
- Templates under `prompt/` are optional. When no prompt is supplied, the script uses its built-in default template, described below.
- Within each data root, including each train/dev/test split, the `schema_path` field in each sample links it to its category definitions under `schema_description/`.

## Unified Schema Representation

### Design

Traditional semantic parsing tasks use different formats and incompatible label systems:

| Task | Traditional format | Challenge |
|:---|:---|:---|
| NER | `{"tokens": [...], "ner_tags": [3, 13, 0, ...]}` | BIO tag sequences require alignment |
| RE | `{"text": "...", "drug": "...", "dosage": "..."}` | Flat key-value pairs leave relation roles implicit |
| EE | `{"event_list": [{"trigger": "...", "arguments": [...]}]}` | Nested structures vary across datasets |
| SLU | `{"intent": "...", "slots": {...}}` | Intents and slots use separate representations |

This dataset unifies these tasks into a **`category` + `args` JSON structure**:

- All category information—entity types, relation types, event types, and intents—is represented by `category`.
- All extracted fields—entity mentions, relation heads and tails, event triggers and arguments, and intent slots—are represented by `args`.

One structure supports all four task types, including multiple categories in one utterance, multiple argument instances, and multi-turn conversations.

### Category Definitions (`schema_description`)

Each dataset has a category definition file under `schema_description/`. It is a JSON array in which each entry defines a candidate category:

| Field | Meaning | Constraints |
|:---|:---|:---|
| `category` | Category name | Used verbatim in model outputs; do not rename it |
| `category_description` | Category meaning, decision criteria, and boundaries | Clear descriptions help distinguish categories; fallback categories can also be defined |
| `args` | List of extractable argument definitions | Each entry contains `name` and `description`; use `[]` for categories without arguments |
| `args[].name` | Argument name: slot, event argument, or role | Used verbatim as a key in model outputs |
| `args[].description` | Extraction rules | Specifies value sources, boundaries, and restrictions |

Example from the smart-device assistant intent schema. Chinese labels and sample content are retained to match the Chinese documentation:

```json
[
  {
    "category": "查询天气",
    "category_description": "了解某地点某时间的天气情况，或者查看天气指数信息。",
    "args": [
      {
        "name": "时间",
        "description": "用户明确提到的时间线索词。"
      },
      {
        "name": "地点",
        "description": "用户查询天气的目标地理位置。支持城市、区县、地标或具体地址。原样返回用户表述，禁止编造。例如：上海、南京、朝阳区、西湖等。"
      },
      {
        "name": "天气指数",
        "description": "必须优先从以下标准名称中精确选择：[湿度、空气质量、紫外线指数……]。"
      }
    ]
  }
]
```

To handle inputs outside the defined categories, add a fallback category such as `其他意图` or `Other` at the end of the category list.

### Task Mapping and Conversion Rules

Public datasets are reconstructed using the following conventions. In-house domain data are annotated directly in this format:

| Task | `category` mapping | `args` mapping | Converted example |
|:---|:---|:---|:---|
| **Intent recognition / slot filling (IR/SLU)** | Intent name | Slots, keyed by slot name | `[{"category": "查询天气", "args": [{"时间": "下周四", "地点": "北京"}]}]` |
| **Named entity recognition (NER)** | Entity type | `mention` for each entity mention | `[{"category": "疾病", "args": [{"mention": "心房内折返性心动过速"}]}]` |
| **Relation extraction (RE)** | Relation type | `subject` + `object` for the head-tail pair | `[{"category": "任职", "args": [{"subject": "马云", "object": "阿里巴巴"}]}]` |
| **Event extraction (EE)** | Event type | `trigger` + argument roles | `[{"category": "股份回购", "args": [{"trigger": "回购", "回购方": "众安集团", "交易金额": "94.56万港元"}]}]` |

Conversion rules:

- **NER**: convert BIO tags or spans into mention objects grouped by entity type. Multiple entities of the same type appear as separate objects with a `mention` key in the category's `args` list.
- **RE**: convert each `(head entity, relation, tail entity)` triple into a category for the relation type, with `subject` and `object` values in an argument object.
- **EE**: use the event type as `category`, and place the trigger and arguments in the same argument object, keyed by `trigger` and the respective role names.
- **IR/SLU**: use the intent name as `category` and slot names as argument keys.
- **Multiple values**: return separate category objects for multiple categories, and separate objects within `args` for independent instances of the same category.

### Unified Output Format

The `output` field stores a serialized JSON string. Parsing it with `json.loads(output)` produces a list with the following structure:

```json
[
    {
        "category": "查询天气",
        "args": [
            {"时间": "明天", "地点": "北京"}
        ]
    }
]
```

- Represent empty arguments as `[]`, not `null`, `{}`, or an omitted field.
- Behavior when no category matches depends on the task instructions, including whether a fallback category is defined and whether the task is single-label. See each dataset's prompt configuration.

## Data Sample

[data_demo.jsonl](examples/data_demo.jsonl) contains one original sample from the smart-device assistant dataset. It uses JSONL format: one JSON object per line, with `output` stored as a JSON string. This sample illustrates the fields and annotations. To run inference or assemble training examples, obtain the schema file referenced by `schema_path` from the full dataset and resolve that path relative to the corresponding data root.

## Data Distribution

### Overview

| Statistic | Value |
|:---|:---|
| **Total samples** | **2,753,000** |
| **Reconstructed public datasets** | **61** |
| **Domains** | **19** (AI, Biomedical, Cybersecurity, Education, Finance, General, etc.) |
| **Languages** | **52** (Chinese, English, Afrikaans, etc.) |
| **Task types** | **4** (NER / RE / EE / IR-SLU) |

### Distribution by Task

| Task | Samples | Share | Representative datasets |
|:---|---:|---:|:---|
| **NER** | 823,000 | 29.9% | MSRA, OntoNotes, CoNLL2003, CMeEE, WeiboNER |
| **RE** | 905,000 | 32.9% | DuIE, NYT, TACRED, BioRED, SemEval |
| **EE** | 56,000 | 2.0% | ACE05, RAMS, FewFC, MAVEN, DuEE |
| **SLU** | 969,000 | 35.2% | Snips, ATIS, MASSIVE |
| **Total** | **2,753,000** | **100%** | — |

### Corpus Composition

<p align="center">
    <img src="figures/fig1_corpus_composition.png" alt="Corpus composition" width="80%">
    <br>
    <b>Figure 1</b>: Corpus distribution by task and domain, and top dataset sources.
</p>

## Dataset Entry Fields

Each JSON file under `dataset/` contains an array, with one sample per element:

```json
{
  "id": "idx",
  "turn": "idx-0",
  "task": "Intent Recognition",
  "source": "XingChen",
  "domain": "Phone",
  "language": "Chinese",
  "schema_path": "./schema_description/schema.json",
  "schema": "",
  "prompt_path": "",
  "prompt": "",
  "dialogs": [
    {"role": "user", "content": "明天的紫外线强度"}
  ],
  "output": "[{\"category\": \"查询天气\", \"args\": [{\"时间\": \"明天\", \"天气指数\": \"紫外线指数\"}]}]"
}
```

| Field | Type | Description |
|:---|:---|:---|
| `id` | str | Unique sample identifier within the dataset |
| `turn` | str | Turn identifier in the form `<sample_id>-<turn_id>`; distinguishes different conversation truncations for the same multi-turn sample |
| `task` | str | Task type: `Intent Recognition` / `NER` / `RE` / `EE` |
| `source` | str | Source dataset name, such as `MTOP` or `CAIS` |
| `domain` | str | Business domain, such as `Banking` or `智能终端助手` (smart-device assistant) |
| `language` | str | Language, such as `Chinese` or `English` |
| `schema_path` | str | Schema file path relative to the directory specified by `--root`, such as `data/General/test` or `data/XingChen`; an initial `./` is allowed |
| `schema` | list/str | An embedded schema must be a non-empty JSON array and then takes precedence over `schema_path`. If no schema is embedded, use an empty string or array and load via `schema_path`. A JSON string cannot substitute for the array |
| `prompt_path` | str | Optional task prompt file path, relative to the directory specified by `--root` |
| `prompt` | str | Embedded prompt template; priority: prompt file > embedded prompt > default template |
| `dialogs` | list | Conversation turns, each containing `role` (`user`/`assistant`) and `content`; single-turn samples have one entry, while multi-turn samples are ordered chronologically and usually end with a user turn |
| `output` | str | Expected output as a JSON string: a serialized `[{category, args}]` list, retained as the supervision target or evaluation reference |

Loading priorities used by `build_examples.py`:

- **Schema**: non-empty embedded `schema` list → file referenced by `schema_path`; an error is raised if neither is available.
- **Prompt**: file referenced by `prompt_path` → embedded `prompt` → built-in default template.
- **System message**: a non-empty `system` field becomes `messages[0]`. This field is unused in the reconstructed public subsets. Otherwise, `messages` contains only one user message.

## Building Training and Inference Examples

The model repository provides [build_examples.py](build_examples.py) under `data/`. It assembles samples into an intermediate format containing metadata, `messages`, and `output`. For SFT, convert this format as required by the training framework—for example, append `output` to `messages` as an assistant reply. For inference, extract `messages` and add API parameters such as `model`; do not send the entire record or the reference answer in `output` to the model.

### Assembly Rules

The script combines each sample's task content into one user message:

```text
Task prompt template
  ├─ {intent_descriptions}  ← Serialized schema text (json.dumps, inserted verbatim)
  ├─ Output format rules   ← Inserted automatically if absent; see below
  └─ {user_input}          ← Rendered dialogs (user → Human, assistant → AI)
```

- **Template placeholders**: custom templates should contain `{intent_descriptions}` to insert the serialized schema. If it is missing, the script neither adds the schema automatically nor raises an error. `{user_input}` is optional; when absent, the dialog text is appended to the template. Automatically inserted format rules appear before the dialog text.
- **Prompt template**: the script first uses the file referenced by `prompt_path` (an object such as `{"system": "..."}`, using its `system` field), then the embedded `prompt`, and finally the built-in default template.
- **Automatic format rules**: if neither `### 输出格式规则` nor `### Output Format` appears in the template, the script inserts output constraints before `{user_input}`. Disable this with `--no_format_rules`.
- **Multi-turn rendering**: turns are rendered chronologically as `RoleName: content`, mapping `user → Human` and `assistant → AI`, with turns separated by newlines.
- **System message**: added at the start of `messages` only when the sample contains a non-empty `system` field; none is added by default.

Each assembled record contains `id / turn / task / source / domain / language / messages / output / prompt_length`.

### Usage Examples

Run the following commands from the model repository root. First download the required data from the [Hugging Face dataset repository](https://huggingface.co/datasets/XingChen-AGI/Xing4.0-29B-Intent-oss/tree/main). Place `General/` and `XingChen/` under `data/` as shown above, preserving their `dataset/`, `schema_description/`, and optional `prompt/` directories.

```bash
# One dataset file -> one examples file
python3 data/build_examples.py \
    --root data/XingChen \
    --dataset intent_recognition_intelligent_phone_dataset.json \
    --save_path out/XingChen/

# Process all dataset files in a split, one output file per dataset
python3 data/build_examples.py --root data/General/test --save_path out/test/

# Write a single dataset as a JSON array (--fmt json)
python3 data/build_examples.py --fmt json --root data/XingChen \
    --dataset intent_recognition_intelligent_phone_dataset.json \
    --save_path out/XingChen/intent_recognition_intelligent_phone_examples.json

# Keep only the first N samples per dataset for debugging
python3 data/build_examples.py --root data/General/test --max_samples 20 --save_path out/debug/

# Disable automatic insertion of output format rules
python3 data/build_examples.py --root data/XingChen --no_format_rules --save_path out/raw/
```

Arguments:

| Argument | Description |
|:---|:---|
| `--root` | Data root containing `dataset/`, `schema_description/`, and optionally `prompt/` |
| `--dataset` | Filename within `dataset/` under `--root`; when omitted, processes all `*.json` files in that directory |
| `--save_path` | An explicit path with an extension is treated as a filename only when processing a single file. For multiple input files, it is always treated as a directory. Directory mode uses `<dataset_name>_examples.jsonl`; when omitted, the default directory is `examples/` under the current working directory. With `--fmt json`, the extension becomes `.json` |
| `--fmt` | `jsonl` (default, one record per line) or `json` (an indented array) |
| `--max_samples` | Maximum number of samples per dataset. Use a positive integer to set a limit; omitted or `0` means no limit. Do not use negative values |
| `--no_format_rules` | Disable automatic insertion of output format rules |

The script skips samples that fail during assembly and continues processing. It prints `built / failed` counts at the end. Check these counts and the failure logs: a normal process exit does not mean every sample was assembled successfully.

### Assembled Example

For the smart-device assistant sample “明天的紫外线强度” (“Tomorrow's UV intensity”) shown above, the following is an excerpt of the assembled `messages[0].content`. The Chinese prompt is retained because the script's built-in default template is in Chinese:

```
### 角色定义
你是一个强大的信息抽取助手，具备意图理解、命名实体识别（NER）、关系抽取（RE）以及事件抽取（EE）等能力。
你可以处理普通文本、单轮输入或多轮对话，并准确提取任务所需信息。

### 任务描述
请根据给定的【字段说明】选择与【输入内容】最匹配的类别，并按照字段格式抽取对应内容。
……

### 字段说明
[{"category": "安装应用", "category_description": "...", "args": [...]}, ...]

### 输出格式规则
1、无论匹配单个还是多个类别，输出一律为 JSON 列表，如 [{"category": "xxx", "args": []}]；
2、args 内元素为键值对：键为【字段说明】中该类别槽位的 name 值（原样使用，禁止改写），值为从【输入内容】中抽取的该槽位实际内容；
3、该类别无槽位时 args 为空数组 []；禁止输出 name、description 字段，禁止输出 JSON 以外的任何文字。

Human: 明天的紫外线强度
```

The corresponding supervision target, `output`, encodes:

```json
[{"category": "查询天气", "args": [{"时间": "明天", "天气指数": "紫外线指数"}]}]
```

### Prompt Conventions for Deployed Services

Use the assembled record's `messages` as the request's message field and add required parameters such as `model` to call a deployed Xing4.0-29B-Intent model or a compatible chat service. Follow these conventions:

- Include one `role: "user"` message containing the task instructions, schema, and conversation. Add a system message according to the template or SDK configuration.
- Insert the schema serialized with `json.dumps(schema, ensure_ascii=False)` verbatim, preserving category and slot names. Changes such as line-by-line rendering, category renaming, or slot key conversion may affect results and require validation.
- Never include test labels or reference answers in inference requests.
- Parse responses with `json.loads` and compare their structures rather than comparing raw strings character by character.

## Usage Guidelines

- **Evaluation protocol**: single-label tasks (intent recognition) allow one category object per sample; multi-label tasks (NER/RE/EE) allow multiple category objects. State the task's constraints in the prompt to keep evaluation consistent.
- **Sample independence**: construct each request independently. Do not accumulate inputs or outputs from other samples, to avoid information leakage.
- **Provenance**: preserve source, domain, language, and other metadata for research and technical auditing.

## License

This dataset is released under the [Apache 2.0](../LICENSE) license. The original license terms of the public source datasets also apply; check their respective terms before commercial use.
