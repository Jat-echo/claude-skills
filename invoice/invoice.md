# 发票整理 Skill

自动从飞书邮箱「发票」文件夹下载所有发票，按实际商品类别和价税合计（小写）金额重命名，整理到指定目录。

## 调用方式

```
/invoice [目标目录]   # 例：/invoice D:\Work\Uah\办公\报销\202606
```

不传参数时默认使用当前月份对应目录（`报销\YYYYMM`）。

---

## 环境依赖

| 组件 | 路径 |
|------|------|
| lark-cli | `C:\Users\Administrator\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\npm\lark-cli.cmd` |
| Python 39（下载用） | `D:\Software\Python\Python39\python.exe` |
| miniconda3（pdfplumber） | `D:\Software\miniconda3\python.exe` |
| 脚本目录 | `D:\Work\Uah\办公\报销\scripts\` |

pdfplumber 安装（首次/SSL 缺失时）：
```
D:\Software\miniconda3\python.exe -m pip install --index-url http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com pdfplumber
```

---

## 执行流程

### Step 0：确认目标目录

```python
OUT_DIR = r"D:\Work\Uah\办公\报销\202606"  # 按月份修改
```

### Step 1：下载发票

```bash
D:\Software\Python\Python39\python.exe scripts\invoice_download.py <OUT_DIR>
```

优先级（对每封邮件依次尝试）：
1. **PDF 附件** — 直接下载
2. **ZIP 附件（通行费电子发票）** — 只提取 `pdf/` 子目录，跳过 `ofd/`、`xml/`、名称含"票据"或"行程"的文件
3. **邮件正文链接** — 匹配 `.pdf`/`dzfp`/`fapiao` 等关键词
4. **百旺 SPA 页面** — 保存 URL 到 `_SPA_*.url.txt`，需浏览器手动/自动下载（见下方"特殊处理"）

### Step 2：重命名

```bash
D:\Software\miniconda3\python.exe scripts\invoice_rename.py <OUT_DIR>
```

- 金额：严格提取 `（小写）¥XXX.XX`（价税合计小写，含税总额）
- 分类规则（按发票商品名称，非渠道）：

| 关键词 | 类别 |
|--------|------|
| 供电 / 充电 / 生活服务 | 充电 |
| 汽油 / 燃油 / 成品油 | 加油费 |
| 药 / 化学药品 / 医疗 | 药品 |
| 电子元件 / 电容 / 电阻 / 集成电路 | 电子器件 |
| 仪器 / 测试 / 检测 / 机械设备 / 电线电缆 | 测试器材 |
| 体育 | 体育用品 |
| 食品 / 餐饮 / 水果 / 肉 / 谷物 / 焙烤 | 食品 |
| 日用 / 洗护 / 家居 / 清洁 / 文具 / 办公 | 日用品 |
| 金属制品 / 五金 / 螺丝 | 五金 |
| 收费公路 / 通行费 / ETC | 通行费 |
| 卖方含"酒店/宾馆/旅馆" | 住宿 |
| 其他 | 其他 |

- 买方验证：名称 `深圳有哈科技有限公司`，税号 `91440300MA5FRA1Q3Q`
- 命名格式：`{类别}_{价税合计小写}.pdf`

### Step 3：去重

```bash
D:\Software\miniconda3\python.exe scripts\invoice_dedup.py <OUT_DIR>
```

按 MD5 哈希比对，保留文件名靠前的那份，删除其余副本。

### Step 4：统计汇总（可选）

```powershell
Get-ChildItem <OUT_DIR> -Filter "*.pdf" | ForEach-Object {
    if ($_.Name -match '_(\d+\.\d{2})') { [double]$Matches[1] }
} | Measure-Object -Sum | Select-Object Count, Sum
```

---

## 特殊处理

### 通行费 ZIP

邮件附件为 `***通行费电子发票.zip`，内含三个子目录：
- `pdf/` ← **只提取这里的文件**
- `ofd/` ← 跳过
- `xml/` ← 跳过

脚本已自动处理（`invoice_download.py` Step B）。

### 百旺 SPA 发票

百旺链接为 Vue.js 单页应用，无法直接 HTTP 下载。处理方式：

1. 从 `_SPA_*.url.txt` 读取链接
2. 用浏览器自动化打开：`https://pis.baiwang.com/smkp-vue/previewInvoiceAllEle?param=...`
3. 等待页面加载（title 变为"发票预览"）
4. 点击右上角"**下载PDF文件**"按钮（CSS selector: `.btn-web`）
5. 文件下载到 `D:\Users\Jat\Downloads\`，从那里复制并按类别重命名到 OUT_DIR

注意：百旺发票项目为 `*体育服务*健身服务费` → 类别 **体育用品**。

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 金额提取错误 | 匹配到"合计"而非"（小写）" | 只用 `（小写）¥` 模式 |
| 通行费下载为票据 | 下载了票据PDF而非发票ZIP | 检查附件名，取包含"发票"的ZIP |
| pdfplumber 读取失败 | OFD/XML 文件被误当 PDF | ZIP 提取时只取 `pdf/` 子目录 |
| pip 安装失败 | SSL 模块缺失 | 使用阿里云 HTTP 镜像安装 |
| 买方税号未找到 | PDF 两栏布局被 pdfplumber 合并 | 视为已知限制，手动确认 |

---

## 注册为 /invoice 斜杠命令

将此文件复制到 Claude Code 全局命令目录即可：

```powershell
Copy-Item "D:\Work\Uah\办公\报销\scripts\invoice.md" `
          "C:\Users\Administrator\.claude\commands\invoice.md"
```

之后在任意 Claude Code 会话中执行 `/invoice` 即可触发本流程。
