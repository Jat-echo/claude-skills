# 知识卡片生成 Skill

将任意长文、书摘、笔记或知识点，自动提炼为结构化内容，并生成高颜值知识卡片插画。

## 调用方式

```
/knowledge-card [内容或主题]
```

- 直接粘贴长文内容，或简述主题
- 不传参数时，Claude 会提示你输入内容

---

## 执行流程

### Step 1：深度提炼（结构化三段论）

对用户输入的内容，按以下三要素进行提炼：

| 要素 | 说明 |
|------|------|
| 核心主题 (Theme) | 用最具穿透力的一句话，定性内容的终极价值 |
| 逻辑脉络 (Structure) | 3-5 个有序关键要点，体现层进或支撑关系，拒绝碎片化 |
| 深度启发 (Insight) | 直击痛点的结论、启发或行动建议，不是复述 |

提炼原则：语言精炼，拒绝套话，字字珠玑。

---

### Step 2：生成知识卡片内容文案

基于 Step 1 的提炼结果，输出卡片正文，格式如下：

```
【标题】{核心主题，≤20字}

【要点】
① {逻辑要点1}
② {逻辑要点2}
③ {逻辑要点3}
...

【启发】
{深度启发，1-2句，直击行动}

【来源/标签】{原文书名/主题标签}
```

---

### Step 3：生成图像

#### 图像提示词（所有方式通用）

```
一张高颜值知识卡片插画，内容如下：

{Step 2 输出的卡片文案}

图像要求：
- 画幅比例：3:1 横向长方形
- 色彩：莫兰迪风格（低饱和度，主色系灰蓝/灰绿/米白/藕粉）
- 背景：Instagram 极简美学，干净留白
- 文字质感：钢笔书写手绘感，优雅排版
- 插图：左侧区域加入与主题直接相关的小型漫画插图
- 布局：左插图区 / 右文字区，底部来源标签
- 整体风格：专业、艺术、视觉吸引力强
```

#### 生图方式优先级

按以下顺序判断当前环境，选择对应方式：

---

**优先：GPT Image 2（`gpt-image-1`）**

默认首选方案，需配置 `OPENAI_API_KEY`：

```python
from openai import OpenAI
import base64

client = OpenAI()  # 需配置 OPENAI_API_KEY 环境变量

def generate_knowledge_card(card_content: str, output_path: str = "card.png"):
    prompt = f"""一张高颜值知识卡片插画，内容如下：

{card_content}

图像要求：
- 画幅比例：3:1 横向长方形（1536x512）
- 色彩：莫兰迪风格（低饱和度，主色系灰蓝/灰绿/米白/藕粉）
- 背景：Instagram 极简美学，干净留白
- 文字质感：钢笔书写手绘感，优雅排版
- 插图：左侧加入与主题相关的小型漫画插图
- 布局：左插图区 / 右文字区，底部来源标签
"""
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024",  # 最接近 3:1 的可用尺寸
        quality="high",
        n=1,
    )
    image_data = base64.b64decode(response.data[0].b64_json)
    with open(output_path, "wb") as f:
        f.write(image_data)
    print(f"知识卡片已保存：{output_path}")
```

> 依赖：`pip install openai` | Key：[platform.openai.com](https://platform.openai.com/api-keys)

---

**Codex 环境：直接生成**

在 OpenAI Codex 环境中运行时，AI 可直接调用图像生成能力，无需额外配置——将上方提示词直接发给 Codex，由 Codex 原生生成图像并返回结果。

---

**兜底：当前客户端原生能力**

若无法调用 GPT Image 2 API，则使用当前所在客户端的图像生成能力：

| 当前客户端 | 生图方式 |
|-----------|---------|
| **Claude**（claude.ai / Claude Code） | 直接将图像提示词发给 Claude，由 Claude 调用其支持的图像生成工具输出图像 |
| **ChatGPT 网页** | 粘贴提示词，ChatGPT 内置 DALL-E / GPT Image 直接生成 |
| **Gemini** | 粘贴提示词，Gemini 调用 Imagen 生成 |
| **其他客户端** | 将提示词提交给该客户端，使用其内置图像生成能力 |

---

### Step 4：使用指引

1. **检查环境** → 有 `OPENAI_API_KEY` 则运行 Python 脚本；在 Codex 则直接生成；否则把提示词发给当前客户端
2. **微调（可选）** → 调整色彩关键词，如"暖棕莫兰迪"、"深色卡片"、"樱花粉系"
3. **合成发布** → 直接使用生成图，或导入排版工具叠加文字后发布

---

## 示例

**输入：**
```
/knowledge-card 《深度工作》核心观点：在无干扰状态下专注于认知要求极高的工作，
能够创造新价值、提升技能，且难以复制。浮浅工作则相反，容易复制，价值低。
```

**Step 1 提炼：**
- 核心主题：专注即竞争力，深度工作是认知经济时代的核心稀缺资源
- 逻辑脉络：①深度工作定义（无干扰专注）→ ②价值（创造力+技能提升）→ ③浮浅工作的陷阱 → ④培养深度工作习惯
- 深度启发：每天保留 2 小时不可打扰的深度时间段，关掉通知，做真正有价值的事

**Step 2 卡片文案：**
```
【标题】深度工作：认知时代的稀缺竞争力

【要点】
① 深度工作 = 无干扰状态下的高强度专注
② 能创造新价值、提升技能，且极难被复制
③ 浮浅工作消耗时间却产出低价值成果
④ 刻意保护"深度时间"是高产出者的共同习惯

【启发】
从今天起，每天保留 2 小时关掉通知的深度时间，
只做当下最重要的一件认知性工作。

【来源】《深度工作》Cal Newport
```

---

## 注册为 /knowledge-card 斜杠命令

```bash
# macOS / Linux
cp knowledge-card.md ~/.claude/commands/knowledge-card.md

# Windows (PowerShell)
Copy-Item "knowledge-card.md" "$env:APPDATA\Claude\commands\knowledge-card.md"
```
