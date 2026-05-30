# 知识卡片生成 Skill

将任意长文、书摘、笔记或知识点，自动提炼为结构化内容，并调用 GPT Image 2 直接生成高颜值知识卡片插画。

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

### Step 3：调用 GPT Image 2 生成卡片插画

使用 OpenAI `gpt-image-1` 模型，将 Step 2 的卡片文案转化为知识卡片图像。

#### 方式 A：通过 ChatGPT 网页（无需 API）

将以下提示词粘贴到 ChatGPT（已开启图像生成的账号）：

```
请根据以下知识卡片内容，生成一张高颜值知识卡片插画：

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

#### 方式 B：通过 OpenAI API（Python）

```python
from openai import OpenAI
import base64

client = OpenAI()  # 需配置 OPENAI_API_KEY 环境变量

def generate_knowledge_card(card_content: str, output_path: str = "card.png"):
    prompt = f"""
请根据以下知识卡片内容生成一张高颜值知识卡片插画：

{card_content}

图像要求：
- 画幅比例：3:1 横向长方形（宽1536px 高512px）
- 色彩：莫兰迪风格（低饱和度，主色系灰蓝/灰绿/米白/藕粉）
- 背景：Instagram 极简美学，干净留白
- 文字质感：钢笔书写手绘感，优雅排版
- 插图：左侧区域加入与主题直接相关的小型漫画插图
- 布局：左插图区 / 右文字区，底部来源标签
- 整体风格：专业、艺术、视觉吸引力强
"""
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024",   # 3:2，最接近 3:1 的可用尺寸
        quality="high",
        n=1,
    )

    image_data = base64.b64decode(response.data[0].b64_json)
    with open(output_path, "wb") as f:
        f.write(image_data)
    print(f"知识卡片已保存到：{output_path}")

# 示例调用
card_content = """
【标题】深度工作：认知时代的稀缺竞争力

【要点】
① 深度工作 = 无干扰状态下的高强度专注
② 能创造新价值、提升技能，且极难被复制
③ 浮浅工作消耗时间却产出低价值成果
④ 刻意保护"深度时间"是高产出者的共同习惯

【启发】
每天保留 2 小时关掉通知的深度时间，只做当下最重要的一件认知性工作。

【来源】《深度工作》Cal Newport
"""
generate_knowledge_card(card_content, "deep_work_card.png")
```

> **依赖安装：** `pip install openai`
> **API Key：** 前往 [platform.openai.com](https://platform.openai.com/api-keys) 获取

---

### Step 4：使用指引

1. **方式 A（推荐新手）** → 复制 Step 3 提示词，打开 ChatGPT，粘贴发送，直接得到图片
2. **方式 B（推荐自动化）** → 配置 `OPENAI_API_KEY`，运行 Python 脚本，图片自动保存本地
3. **微调（可选）** → 在提示词中调整色彩关键词，如"暖棕莫兰迪"、"深色卡片"、"樱花粉系"
4. **合成发布** → 直接使用生成图，或导入排版工具叠加文字后发布

---

## GPT Image 2 自动化（批量制卡）

对多条知识点批量生成卡片：

```python
import os
from openai import OpenAI
import base64

client = OpenAI()

topics = [
    ("深度工作", "《深度工作》Cal Newport"),
    ("第一性原理", "埃隆·马斯克思维方式"),
    # 添加更多主题...
]

for title, source in topics:
    # 此处接入 Step 1 提炼逻辑（可用 Claude API 自动提炼）
    card_content = f"【标题】{title}\n【来源】{source}"
    output_file = f"card_{title}.png"

    response = client.images.generate(
        model="gpt-image-1",
        prompt=f"知识卡片，莫兰迪风，3:1横版，钢笔手绘感，内容：{card_content}",
        size="1536x1024",
        quality="high",
        n=1,
    )
    image_data = base64.b64decode(response.data[0].b64_json)
    with open(output_file, "wb") as f:
        f.write(image_data)
    print(f"✓ {output_file}")
```

---

## 示例

**输入：**
```
/knowledge-card 《深度工作》核心观点：在无干扰状态下专注于认知要求极高的工作，
能够创造新价值、提升技能，且难以复制。浮浅工作则相反，容易复制，价值低。
```

**Step 1 提炼输出：**
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

之后在任意 Claude Code 会话中执行 `/knowledge-card` 即可触发本流程。
