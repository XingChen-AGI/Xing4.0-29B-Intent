<h1 align="center">Xing4.0-29B-Intent</h1>

<p align="center"><strong>Xing4.0-29B-Intent</strong> — 基于 29B MoE（每 token 仅激活 4B 参数）的 Schema 引导意图识别与结构化信息抽取模型。</p>

<p align="center">
  🤗 <a href="https://huggingface.co/XingChen-AGI/Xing4.0-29B-Intent">Hugging Face</a> •
  🤖 <a href="https://www.modelscope.cn/models/XingChen-AGI/Xing4.0-29B-Intent">ModelScope</a> •
  🪐 <a href="https://modelers.cn/models/XingChen-AGI/Xing4.0-29B-Intent" target="_blank">Modelers</a> •
  📚 <a href="https://huggingface.co/datasets/XingChen-AGI/Xing4.0-29B-Intent-oss">Dataset</a>
</p>

<div align="center">

[English](./README.md) | [简体中文](./README_zh.md)

</div>


## 目录

- [项目介绍](#项目介绍)
- [模型信息](#模型信息)
- [评测结果](#评测结果)
- [快速开始](#快速开始)
- [配套数据](#配套数据)
- [许可与引用](#许可与引用)

## 项目介绍

**Xing4.0-29B-Intent** 是基于中电信人工智能科技有限公司星辰语义大模型 [Xing4.0-29B-A4B](https://github.com/XingChen-AGI/Xing4.0-29B-A4B) 研发的 **Schema 引导意图识别与结构化信息抽取模型**，面向智能助手、业务分流和文档信息整理等场景，将自然语言转化为业务系统可读取的结构化结果。

在实际业务中，用户的一句“帮我查明天北京到上海的航班”，需要被解析为“查询航班”这一意图，以及出发地、目的地、日期等参数。Xing4.0-29B-Intent 根据输入的类别与字段定义完成识别和抽取，并以统一的 JSON 格式返回结果。

### 核心特性

- **四类任务，统一表达**：支持意图识别与槽位填充、命名实体识别、关系抽取和事件抽取，统一使用 `category + args` 描述结果。
- **Schema 引导，按需定义业务**：通过候选类别、类别描述及字段定义指定任务，复用同一套输入输出协议适配不同业务。
- **识别与抽取一体化**：同时获取用户意图和相关参数，支持用 JSON 数组表达多个类别及多组参数实例。
- **覆盖中英文场景**：评测覆盖中英文语料，可用于对话中的意图理解与文本中的结构化信息提取。
- **配套 SDK，便于接入**：提供 Schema 定义、提示词组装、多轮对话输入、同步与异步调用，以及结构化结果访问。

## 模型信息

| 项目 | 说明 |
| --- | --- |
| 模型名称 | Xing4.0-29B-Intent |
| 基座模型 | [Xing4.0-29B-A4B](https://huggingface.co/XingChen-AGI/Xing4.0-29B-A4B) |
| 基座参数规模 | 总参数约 29B，每 token 激活约 4B |
| 定位 | Schema 引导的意图识别与结构化信息抽取 |
| 支持任务 | 意图识别与槽位填充、命名实体识别、关系抽取、事件抽取 |
| 输入 | 任务说明、Schema、文本或对话 |
| 输出 | JSON 数组，每项包含 `category` 与 `args` |
| 语言 | 中文、英文 |

基座采用 MoE 架构，技术细节见 [基座模型介绍](https://github.com/XingChen-AGI/Xing4.0-29B-A4B)。本项目重点展示意图与信息抽取能力，具体业务效果需结合目标数据和 Schema 验证。

### 任务与输出

| 任务 | `category` 的含义 | `args` 的内容 |
| --- | --- | --- |
| 意图识别与槽位填充 | 用户意图 | 意图对应的业务参数 |
| 命名实体识别 | 实体类别 | 按 Schema 字段抽取的实体信息 |
| 关系抽取 | 关系类别 | 参与关系的实体等字段 |
| 事件抽取 | 事件类别 | 事件参与者、时间、地点等字段 |

输入 Schema 定义候选类别及其待抽取字段，其中 `category` 指定类别名称，`args` 列出各字段的名称与描述。模型输出使用相应的类别名称和字段名称，`args` 中每个对象表示一组抽取到的参数实例；没有可填写参数时，`args` 为 `[]`。

## 评测结果

我们在意图理解、命名实体识别、关系抽取和事件抽取四类任务上评估模型表现。下表展示当前整理的评测结果，分值以百分制展示，并按原始结果四舍五入至整数。

| 模型 | 总分 | 类别分值 | 事件抽取分值 | 命名实体识别分值 | 关系抽取分值 | 意图理解分值 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Xing4.0-29B-Intent** | **58** | 69 | **40** | **72** | **38** | **81** |
| Gemini-3.6-Flash | 49 | **71** | 30 | 71 | 29 | 64 |
| Qwen3.8-Max | 46 | 71 | 29 | 66 | 26 | 63 |
| Kimi-K3 | 45 | 71 | 28 | 68 | 25 | 61 |
| GPT-5.6-Sol | 45 | 70 | 28 | 68 | 23 | 60 |
| GLM-5.2 | 44 | 70 | 29 | 65 | 25 | 58 |
| GLM-5.3-Flash | 44 | 69 | 27 | 65 | 26 | 58 |
| DeepSeek-V4.1-Flash | 42 | 67 | 26 | 61 | 23 | 56 |
| DeepSeek-V4-Pro | 41 | 67 | 23 | 60 | 24 | 56 |
| LongCat-2.0 | 41 | 68 | 24 | 62 | 23 | 53 |
| GPT-6-Luna | 39 | 64 | 24 | 59 | 20 | 51 |

注：加粗表示该列原始分值最高，按四舍五入前的小数判定；整数显示相同不代表原始分值并列。

### 评测说明

- **评测数据**：测试集由从 48 个公开数据集中抽取的 6,000 条样本组成，覆盖命名实体识别、关系抽取、事件抽取和意图理解四类任务，用于评估模型依据给定的任务说明与 Schema，从输入文本中识别类别并抽取相关信息的能力。
- **分值含义**：四类任务分值为各数据集字段值 Micro-F1 的宏平均，总分为四类任务分值的等权平均；类别分值仅评估 category 标签，并同样对四类任务等权汇总。分值以百分制展示，不等于业务准确率。
- **解释边界**：类别分值不代表所有字段均正确；不同接口、提示词及推理配置也可能影响结果。

## 快速开始

### 启动模型服务

模型服务的环境准备与启动方式可参考基座模型的 [服务化推理说明](https://github.com/XingChen-AGI/Xing4.0-29B-A4B/blob/main/README_zh.md#服务化推理)，其中包含 vLLM、SGLang 等框架的适配环境与部署教程。

使用本模型时，请将教程中的模型路径替换为 **Xing4.0-29B-Intent 权重路径**，并将 `--served-model-name` 设置为 `Xing4.0-29B-Intent`。推理框架的适配要求以基座部署文档为准，显存、并行度及上下文长度按实际环境配置。

启动后，SDK 通过服务提供的 OpenAI 兼容接口调用模型。下面以 `http://localhost:8000/v1` 为例。

### 安装与使用 SDK

通过配套的 [XingIntent SDK](XingIntentSDK/README_zh.md)，可以定义业务意图并直接获取结构化结果。下载或克隆本仓库后，在仓库根目录执行以下命令安装 SDK：

```bash
cd XingIntentSDK
python -m pip install -e .
```

安装完成后，使用以下示例调用模型服务；请将 `base_url` 和 `model` 替换为实际服务地址与模型名称。

```python
from xingintent import Arg, Intent, IntentClient

client = IntentClient(
    base_url="http://localhost:8000/v1",
    model="Xing4.0-29B-Intent",
    max_tokens=512,
)
result = client.predict(
    text="帮我查明天北京到上海的航班。",
    intents=[
        Intent(
            "查询航班",
            "查询指定日期与路线的航班",
            args=[
                Arg("出发地", "出发城市"),
                Arg("目的地", "到达城市"),
                Arg("日期", "用户提到的出行日期，保留原文"),
            ],
        )
    ],
)
print(result.category)
print(result.args)
```

上述代码的期望打印结果：

```text
查询航班
{'出发地': '北京', '目的地': '上海', '日期': '明天'}
```

`result.category` 和 `result.args` 是 SDK 提供的便捷访问属性，分别返回第一个识别类别及其合并后的参数字典。对于多类别或多组参数实例，请遍历 `result.intents` 并读取各项的 `category` 和 `args`，以保留完整结构。

SDK 自动完成提示词组装和结果解析。多轮对话、异步调用、Schema 文件加载及约束解码等详细用法，参阅 [SDK 中文文档](XingIntentSDK/README_zh.md)；更多示例见 [SDK examples](XingIntentSDK/examples/)。

## 配套数据

本项目同步开源配套数据集 **Xing4.0-29B-Intent-oss**，将 **61 个公开数据集**与**电信自建的智能终端助手领域数据**纳入统一的 Schema 引导表示体系。数据集共约 **275 万条样本**，覆盖 **4 类任务、19 个领域、52 种语言**，并配套包含 **170+ 意图、148 个槽位**的智能助手标准标签集，为模型微调、评测与业务落地提供可复用的**数据与任务定义**。

- **统一格式，复用处理流程**：将意图识别与槽位填充（SLU）、命名实体识别（NER）、关系抽取（RE）和事件抽取（EE）统一为 `category + args` 格式，减少跨任务的数据转换工作，便于复用处理与训练流程。
- **通用语料与业务场景双覆盖**：结合公开语料的任务与领域广度，以及智能终端助手场景的意图与槽位标注，兼顾通用能力研究和业务适配。
- **配套标签体系，加快任务定义**：提供智能助手意图与槽位定义，可作为新项目的初始 Schema，并按业务需求裁剪或扩展，减少从零设计标签体系的工作。
- **灵活组合数据，支持业务定制**：可从开源数据中按需采样，与自建业务数据按比例混合进行监督微调（SFT）；配套 Schema 与样例构建脚本，衔接任务定义、数据准备和模型训练。

<p align="center">
  <img src="data/figures/fig1_corpus_composition.png" alt="各任务内部的领域占比与主要来源数据集的样本规模" width="100%">
  <br>
  <em>各任务的领域分布（左）与主要数据来源规模（右）。</em>
</p>

- [Hugging Face 数据集主页](https://huggingface.co/datasets/XingChen-AGI/Xing4.0-29B-Intent-oss)：查看数据集介绍。
- [数据说明](data/README_zh.md)：查看详细分布、Schema、字段定义和样例构建方式。

## 许可与引用

### 开源许可

本项目的模型权重、公开数据和代码（含 Python SDK）均采用 [Apache License 2.0](LICENSE)。

### 引用

如果本项目对你的研究或应用有帮助，欢迎引用本项目及基座模型的相关工作。

```bibtex
@misc{liu2025trainingreporttelechat3moe,
      title={Training Report of TeleChat3-MoE}, 
      author={Xinzhang Liu and Chao Wang and Zhihao Yang and Zhuo Jiang and Xuncheng Zhao and Haoran Wang and Lei Li and Dongdong He and Luobin Liu and Kaizhe Yuan and Han Gao and Zihan Wang and Yitong Yao and Sishi Xiong and Wenmin Deng and Haowei He and Kaidong Yu and Yu Zhao and Ruiyu Fang and Yuhao Jiang and Yingyan Li and Xiaohui Hu and Xi Yu and Jingqi Li and Yanwei Liu and Qingli Li and Xinyu Shi and Junhao Niu and Chengnuo Huang and Yao Xiao and Ruiwen Wang and Fengkai Li and Luwen Pu and Kaipeng Jia and Fubei Yao and Yuyao Huang and Xuewei He and Zhuoru Jiang and Ruiting Song and Rui Xue and Qiyi Xie and Jie Zhang and Zilu Huang and Zhaoxi Zhang and Zhilong Lu and Yanhan Zhang and Yin Zhang and Yanlei Xue and Zhu Yuan and Teng Su and Xin Jiang and Shuangyong Song and Yongxiang Li and Xuelong Li},
      year={2025},
      eprint={2512.24157},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2512.24157}, 
}

@misc{wang2025technicalreporttelechat2telechat25,
      title={Technical Report of TeleChat2, TeleChat2.5 and T1}, 
      author={Zihan Wang and Xinzhang Liu and Yitong Yao and Chao Wang and Yu Zhao and Zhihao Yang and Wenmin Deng and Kaipeng Jia and Jiaxin Peng and Yuyao Huang and Sishi Xiong and Zhuo Jiang and Kaidong Yu and Xiaohui Hu and Fubei Yao and Ruiyu Fang and Zhuoru Jiang and Ruiting Song and Qiyi Xie and Rui Xue and Xuewei He and Yanlei Xue and Zhu Yuan and Zhaoxi Zhang and Zilu Huang and Shiquan Wang and Xin Wang and Hanming Wu and Mingyuan Wang and Xufeng Zhan and Yuhan Sun and Zhaohu Xing and Yuhao Jiang and Bingkai Yang and Shuangyong Song and Yongxiang Li and Zhongjiang He and Xuelong Li},
      year={2025},
      eprint={2507.18013},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2507.18013}, 
}
```
