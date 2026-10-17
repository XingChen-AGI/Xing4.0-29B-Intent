<h1 align="center">Xing4.0-29B-Intent-oss</h1>

<div align="center">

[English](./README.md) | [简体中文](./README_zh.md)

</div>

本数据集是 [Xing4.0-29B-Intent](../README_zh.md) 意图决策与结构化信息抽取模型的配套数据（下文统一简称 **Xing4.0-29B-Intent-oss**），由中电信人工智能科技有限公司星辰通用人工智能实验室整理开源。

Xing4.0-29B-Intent 根据调用方提供的候选类别集合（Schema），在一次推理中同时完成**类别判定与参数抽取**，输出业务系统可直接读取的结构化结果。模型的能力来自两类数据：

- **公开数据重构**：将 61 个开源信息抽取与口语理解数据集，统一重构到 Schema 引导的统一表示体系（覆盖 NER/RE/EE/SLU 四类任务，下文详述）；
- **电信自建领域数据集（智能终端助手场景）**：面向智能终端助手场景沉淀的意图与槽位标注数据。

两类数据用于训练模型根据 Schema 理解类别与抽取字段的能力。新增业务可通过定义 Schema 与提供示例进行适配，具体效果需结合目标业务数据验证。

## 数据能用来做什么

- **模型训练（SFT）**：以 `messages` + `output` 构造训练样本，用于训练 Chat 格式模型在四类任务上的结构化输出能力；
- **模型评测**：可用于 Schema 引导的语义理解评测，覆盖意图识别/槽位填充、命名实体识别、关系抽取、事件抽取；复现特定评测结果还需使用一致的数据版本、评测脚本与推理配置；
- **冷启动测试**：跨任务、跨领域、跨语言地考察模型对未见 Schema 的泛化能力，评估"换业务只换配置"的落地成本；
- **提示词与格式研究**：所有任务共用一套"任务说明 + Schema + 输入"的提示词组装协议，可对比研究 Schema 表述、类别粒度对解析效果的影响。

## 目录结构

```

data/
├── General/                    # 公开数据集重构（按 split 组织）
│   ├── train/
│   │   ├── dataset/               # 训练样本，按数据集命名，如 MTOP.json
│   │   ├── schema_description/    # 对应的类别定义文件
│   │   └── prompt/                # 可选：任务级提示词模板
│   ├── dev/                       # 结构同上
│   └── test/                      # 结构同上
├── XingChen/                        # 电信自建领域数据集（智能终端助手场景）
│   ├── dataset/
│   ├── schema_description/
│   └── prompt/
└── build_examples.py              # examples 构建脚本
```

- `General/<split>/` 与 `XingChen/` 采用相同的数据组织结构，均包含 `dataset/`、`schema_description/` 及可选的 `prompt/`，`build_examples.py` 对两类数据的处理方式相同；
- `prompt/` 下的模板为可选配置：不提供时脚本使用内置默认模板（见下文）；
- 同名任务目录下（含 train/dev/test），`schema_description/` 与 `dataset/` 中的文件通过条目内的 `schema_path` 字段关联。

## 统一 Schema 表示体系

### 设计理念

传统语义解析任务格式各异、标签体系互不兼容：

| 任务 | 传统格式 | 问题 |
|:---|:---|:---|
| NER | `{"tokens": [...], "ner_tags": [3, 13, 0, ...]}` | BIO 标签序列需对齐 |
| RE | `{"text": "...", "drug": "...", "dosage": "..."}` | 扁平键值对，关系角色隐式 |
| EE | `{"event_list": [{"trigger": "...", "arguments": [...]}]}` | 嵌套结构，各数据集自成一套 |
| SLU | `{"intent": "...", "slots": {...}}` | 意图与槽位两套体系 |

本数据集将上述任务统一到 **`category` + `args` 的 JSON 层级结构**：

- 实体类型、关系类型、事件类型、意图等所有"类别"信息统一放入 `category`；
- 实体提及、关系头尾实体、事件触发词与论元、意图槽位等所有"字段"统一放入 `args`。

一套结构覆盖四类任务，天然支持一句话多类别、多组参数实例、多轮对话。

### 标签库定义（schema_description）

每个数据集在 `schema_description/` 下有一个类别定义文件，为 JSON 数组，逐条声明候选类别。字段含义：

| 字段 | 含义 | 约束 |
|:---|:---|:---|
| `category` | 类别名 | 模型输出时使用的名称，原样使用、禁止改写 |
| `category_description` | 类别含义、判断条件与边界 | 清晰的描述有助于模型理解标签边界，支持兜底类别定义 |
| `args` | 可抽取参数定义列表 | 每项含 `name` 与 `description`；无参数时为 `[]` |
| `args[].name` | 参数名（槽位/论元/角色名） | 输出结果的键名，原样使用、禁止改写 |
| `args[].description` | 参数抽取规则 | 界定取值来源、边界与禁止事项 |

定义示例（取自智能终端助手场景意图库）：

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

如需兜底意图（涵盖未被定义的输入），在类别集合最后定义 `其他意图` 或 `Other` 类别即可。

### 任务映射标准与转换规则

公开数据集按以下统一标准重构（领域自建数据集直接按该标准标注）：

| 任务 | `category` 映射 | `args` 映射 | 转换后示例 |
|:---|:---|:---|:---|
| **意图识别/槽位填充（IR/SLU）** | 意图名 | 各槽位（键为槽位名） | `[{"category": "查询天气", "args": [{"时间": "下周四", "地点": "北京"}]}]` |
| **命名实体识别（NER）** | 实体类型 | `mention`（各实体提及） | `[{"category": "疾病", "args": [{"mention": "心房内折返性心动过速"}]}]` |
| **关系抽取（RE）** | 关系类型 | `subject` + `object`（头尾实体对） | `[{"category": "任职", "args": [{"subject": "马云", "object": "阿里巴巴"}]}]` |
| **事件抽取（EE）** | 事件类型 | `trigger` + 各论元角色 | `[{"category": "股份回购", "args": [{"trigger": "回购", "回购方": "众安集团", "交易金额": "94.56万港元"}]}]` |

转换要点：

- **NER**：BIO/片段序列 → 每个"实体类型 + 提及文本"生成一个对象，同类型多个实体并列在 `args` 列表（多个 `mention` 键对）；
- **RE**：三元组 `(头实体, 关系, 尾实体)` → `category` 取关系类型，头/尾实体分别作为 `subject`、`object` 的值；
- **EE**：触发词识别 + 论元填充 → `category` 取事件类型，触发词与各论元按角色名作为键值对放入同一 `args` 对象；
- **IR/SLU**：意图判定 + 槽位填充 → `category` 取意图名，各槽位名直接作为键；
- **多值兼容**：一句话涉及多个类别 → 输出多个并列对象；同一类别下多组独立参数实例 → `args` 中多个对象。

### 统一输出格式

`output` 字段存储序列化后的 JSON 字符串，使用 `json.loads(output)` 解析后的结构为以下列表：

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

- 空 `args` 用 `[]` 表示，禁止用 `null`、`{}` 或省略字段代替；
- 无匹配类别时的行为由任务说明（是否定义兜底类别、是否限定单标签）决定，见各数据集的 prompt 配置。

## 数据样例

[data_demo.jsonl](examples/data_demo.jsonl) 收录一条智能终端助手数据集的原始样本，以 JSONL 格式展示（每行一个 JSON 对象，`output` 为 JSON 字符串）。该样例用于说明字段与标注格式；运行推理或构建训练样本时，还需从完整数据集获取 `schema_path` 指向的 Schema 文件，并以对应的数据根目录解析该路径。

## 数据分布

### 规模概览

| 统计项 | 数值 |
|:---|:---|
| **总样本数** | **2,753,000** |
| **重构公开数据集** | **61 个** |
| **覆盖领域** | **19 个**（AI、Biomedical、Cybersecurity、Education、Finance、General 等） |
| **覆盖语言** | **52 种**（中文、英文、南非语等） |
| **任务类型** | **4 类**（NER / RE / EE / IR-SLU） |

### 按任务类型分布

| 任务类型 | 样本数 | 占比 | 代表性数据集 |
|:---|---:|---:|:---|
| **NER** | 823,000 | 29.9% | MSRA, OntoNotes, CoNLL2003, CMeEE, WeiboNER |
| **RE** | 905,000 | 32.9% | DuIE, NYT, TACRED, BioRED, SemEval |
| **EE** | 56,000 | 2.0% | ACE05, RAMS, FewFC, MAVEN, DuEE |
| **SLU** | 969,000 | 35.2% | Snips, ATIS, MASSIVE |
| **总计** | **2,753,000** | **100%** | — |

### 语料构成

<p align="center">
    <img src="figures/fig1_corpus_composition.png" alt="fig1_corpus_composition" width="80%">
    <br>
    <b>图1</b>：语料库分布统计（任务-领域构成 / Top 数据集源）
</p>

## 数据字段说明（dataset 条目）

`dataset/` 下每个 JSON 文件为一个数组，每个元素代表一条样本：

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

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `id` | str | 样本条目唯一编号（数据集内唯一） |
| `turn` | str | 轮次标识，格式 `<样本id>-<轮次id>`；多轮样本中用于区分同一样本的不同截断轮 |
| `task` | str | 任务类型：`Intent Recognition` / `NER` / `RE` / `EE` |
| `source` | str | 来源数据集名称，如 `MTOP`、`CAIS` |
| `domain` | str | 业务领域，如 `Banking`、`智能终端助手` |
| `language` | str | 语言：`Chinese` / `English` 等 |
| `schema_path` | str | 所用类别定义文件相对路径，相对于 `--root` 指定的目录（如 `data/General/test` 或 `data/XingChen`），可使用 `./` 前缀 |
| `schema` | list/str | 内嵌 Schema 必须为非空 JSON 数组，此时优先于 `schema_path`；未内嵌时可留空字符串或空数组，通过 `schema_path` 加载。不支持用 JSON 字符串代替数组 |
| `prompt_path` | str | 任务级提示词模板文件相对路径，相对于 `--root` 指定的目录（可选） |
| `prompt` | str | 内嵌提示词模板，非空时优先级：prompt 文件 > 内嵌 prompt > 默认模板 |
| `dialogs` | list | 对话内容，每项含 `role`（`user`/`assistant`）与 `content`；单轮样本即一项，多轮按时间顺序排列，最后一轮通常为 user |
| `output` | str | 期望输出，JSON 字符串（序列化的 `[{category, args}]` 列表），原样直接作为监督信号或评测标准答案 |

字段优先级规则（`build_examples.py` 拼装时遵循）：

- **Schema 加载**：内嵌 `schema`（非空 list）→ `schema_path` 指向的文件，两者都不可用时报错；
- **Prompt 加载**：`prompt_path` 文件 → 内嵌 `prompt` → 内置默认模板；
- **system 注入**：条目含非空 `system` 字段（公开重构子集未使用）时作为 messages[0]，否则 messages 仅一条 user。

## 如何构建训练/推理 examples

仓库的 `data/` 目录提供 [build_examples.py](build_examples.py)，可将上述目录中的样本拼装为包含元信息、`messages` 与 `output` 的训练与推理中间格式。用于 SFT 时，需按训练框架要求转换，例如将 `output` 作为 assistant 回复追加到 `messages`；用于推理时，应提取 `messages` 并补充 `model` 等接口参数，不要将整条记录或标准答案 `output` 发送给模型。

### 拼装规则

脚本将每条样本拼装为单条 user 消息：

```
任务提示词模板
  ├─ {intent_descriptions}  ← Schema 序列化文本（json.dumps，原样填入，不做渲染改写）
  ├─ 输出格式规则（模板未自带时自动插入，见下）
  └─ {user_input}          ← dialogs 渲染文本（user→Human，assistant→AI，每轮一行）
```

- **模板占位符**：自定义模板应包含 `{intent_descriptions}`，用于插入序列化后的 Schema；缺少该占位符时，脚本不会自动补入 Schema，也不会报错。`{user_input}` 为可选占位符，缺少时对话文本会追加到模板末尾；启用自动格式规则时，规则位于对话文本之前。
- **提示词模板**：优先用条目 `prompt_path` 指向的文件（`{"system": "..."}` 结构，取其 `system` 字段），其次条目内嵌 `prompt`，都没有时使用内置默认模板；
- **格式规则自动插入**：若模板中不含 `### 输出格式规则` 或 `### Output Format` 标题，脚本会在 `{user_input}` 前自动插入输出格式约束段（`--no_format_rules` 可关闭）；
- **多轮渲染**：所有轮次按时间顺序逐轮渲染，角色映射 `user → Human`、`assistant → AI`，格式为每轮一行 `角色名: 内容`；
- **system 消息**：仅当条目 `system` 字段非空时置于 messages 首位，默认不注入任何 system。

拼装结果每行包含：`id / turn / task / source / domain / language / messages / output / prompt_length`。

### 使用示例

以下命令均在模型仓库根目录执行。请先从 [Hugging Face 数据集仓库](https://huggingface.co/datasets/XingChen-AGI/Xing4.0-29B-Intent-oss/tree/main) 下载所需数据，将 `General/`、`XingChen/` 按上述目录结构放入 `data/`，保留各自的 `dataset/`、`schema_description/` 及可选的 `prompt/`。

```bash
# 单个数据集文件 → 一个 examples 文件
python3 data/build_examples.py \
    --root data/XingChen \
    --dataset intent_recognition_intelligent_phone_dataset.json \
    --save_path out/XingChen/

# 处理一个 split 下全部 dataset 文件，每个数据集一个输出文件
python3 data/build_examples.py --root data/General/test --save_path out/test/

# 单个数据集输出为 JSON 数组（--fmt json）
python3 data/build_examples.py --fmt json --root data/XingChen \
    --dataset intent_recognition_intelligent_phone_dataset.json \
    --save_path out/XingChen/intent_recognition_intelligent_phone_examples.json

# 只取每个数据集前 N 条（构建调试样例）
python3 data/build_examples.py --root data/General/test --max_samples 20 --save_path out/debug/

# 关闭自动插入的输出格式规则段
python3 data/build_examples.py --root data/XingChen --no_format_rules --save_path out/raw/
```

参数说明：

| 参数 | 说明 |
|:---|:---|
| `--root` | 数据根目录，需包含 `dataset/`、`schema_description/`（及可选 `prompt/`） |
| `--dataset` | 指定 `--root` 下 `dataset/` 内的文件名；缺省处理该目录下全部 `*.json` |
| `--save_path` | 仅处理单个文件且路径带扩展名时，按指定文件路径输出；处理多个文件时始终视为目录。目录模式按 `<数据集名>_examples.jsonl` 命名，留空时默认写入当前工作目录的 `examples/`；使用 `--fmt json` 时扩展名改为 `.json` |
| `--fmt` | `jsonl`（默认，每行一条）或 `json`（缩进数组） |
| `--max_samples` | 每个数据集最多取前 N 条，限量时请传正整数；省略或传 `0` 均表示不限制数量，不要传负数 |
| `--no_format_rules` | 不自动插入输出格式规则段 |

脚本会跳过构建失败的样本并继续处理，完成后打印 `built / failed` 数量。请核对该统计及失败日志；进程正常结束不代表所有样本均已成功构建。

### 构建结果样例

以智能终端助手场景的 "明天的紫外线强度"（见上文条目）为例，构建后 messages[0] 的 content（节选）：

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

对应监督目标 `output`：

```json
[{"category": "查询天气", "args": [{"时间": "明天", "天气指数": "紫外线指数"}]}]
```

### 部署服务时的提示词约定

将 `build_examples.py` 生成记录中的 `messages` 作为请求的消息字段，并补充 `model` 等必要参数，即可调用部署后的 Xing4.0-29B-Intent 或兼容的 Chat 服务。调用时遵循模型使用说明中的约束：

- 每次请求只发送一条 `role: "user"` 消息，任务说明、Schema 与对话内容统一放入一条 user 消息；system 消息按所用模板或 SDK 配置添加；
- Schema 以 `json.dumps(schema, ensure_ascii=False)` 序列化后原样填入，保持类别名与槽位键名一致。逐行渲染、类别名改写或槽位键名转换等变更可能影响效果，需重新验证；
- 测试标签与标准答案不得进入请求；
- 读取模型返回后，用 `json.loads` 解析再比较结构，不要按字符串逐字比较。

## 使用规范与注意事项

- **评测口径**：单标签任务（意图识别）每条样本只允许一个类别对象；多标签任务（NER/RE/EE）允许多个对象并列。构造提示词时按任务在说明中限定，避免评测口径不一致；
- **样本独立性**：每条样本独立构造请求，禁止累积其他样本的输入或输出，避免信息泄漏；
- **来源标注**：数据来源、领域、语言等元信息字段原样保留，供研究与技术审计使用。

## 许可证

本数据集采用 [Apache 2.0](../LICENSE) 许可证开源。各公开源数据集的原有许可条款同样适用，商用前请核对对应源数据集的授权要求。
