# -*- coding: utf-8 -*-
"""
Step 2: Read all PDFs in OUT_DIR, extract correct amount (价税合计小写),
classify by item content, verify buyer, and rename to {类别}_{金额}.pdf.

Usage: python invoice_rename.py <OUT_DIR>
Requires: pdfplumber (pip install pdfplumber via aliyun mirror if SSL absent)
  pip install --index-url http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com pdfplumber
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
import pdfplumber

OUT_DIR    = sys.argv[1] if len(sys.argv) > 1 else r"D:\Work\Uah\办公\报销\202605"
BUYER_NAME = "深圳有哈科技有限公司"
BUYER_TAX  = "91440300MA5FRA1Q3Q"

# ── PDF helpers ───────────────────────────────────────────────────────────

def read_pdf(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)

def get_amount(text):
    """Extract 价税合计（小写） — the tax-inclusive definitive total."""
    m = re.search(r'[（(]小写[）)]\s*[¥￥]\s*([\d,]+\.\d{2})', text)
    if m: return m.group(1).replace(',', '')
    # (小写) 与 ¥ 跨行时：取「大写金额行」末尾紧跟的 ¥ 小写数字
    m = re.search(r'[壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]{2,}\s*[¥￥]\s*([\d,]+\.\d{2})', text)
    if m: return m.group(1).replace(',', '')
    m = re.search(r'价税合计\s*[¥￥]\s*([\d,]+\.\d{2})', text)
    if m: return m.group(1).replace(',', '')
    return None

def get_seller(text):
    m = re.search(r'销\s*名\s*称\s*[：:]\s*(.{2,30}?)[\s\n]', text)
    return m.group(1).strip() if m else ""

def get_category(text, seller=""):
    """Classify by actual purchased item content, not by channel/retailer."""
    items = re.findall(r'\*([^*\n]+)\*([^*\n]*)', text)
    # 同时纳入星号大类(如 生产生活服务)与其后的具体商品名(如 餐饮服务)，
    # 否则「*生产生活服务*餐饮服务」只会看到「生活服务」而误判为充电
    cats  = " ".join((c + " " + d).strip() for c, d in items).lower()

    # 通行费 — check full text for toll keywords
    if any(k in text for k in ['收费公路', '通行费', 'ETC', '路桥']):
        return '通行费'
    if '通行' in cats or '过路' in cats:
        return '通行费'

    # 住宿 — seller is a hotel
    if any(k in seller for k in ['酒店', '宾馆', '旅馆', '旅店']):
        return '住宿'
    if '住宿' in cats:
        return '住宿'

    rules = [
        # 先匹配明确的「充电/用电」，避免下面的餐饮被「生活服务」提前吞掉
        (['供电', '电费', '充电服务', '充电桩', '换电'],                     '充电'),
        (['汽油', '燃油', '成品油'],                                        '加油费'),
        (['药', '化学药品', '医疗', '保健'],                                 '药品'),
        (['电子元件', '电子', '电容', '电阻', '集成电路', '半导体'],            '电子器件'),
        (['仪器', '测试', '检测', '量具', '机械设备', '配电控制', '电线电缆'],  '测试器材'),
        (['体育'],                                                          '体育用品'),
        (['食品', '水果', '肉', '餐饮', '饮料', '蔬菜', '谷物', '焙烤',
          '糖果', '方便食品', '熟肉', '果类', '乳制品', '调味', '零食'],      '食品'),
        (['日用', '杂品', '洗护', '家居', '清洁', '纸品', '文具', '办公'],    '日用品'),
        (['金属制品', '五金', '螺丝', '零件'],                               '五金'),
        # 兜底：仅「生活服务」而无具体商品的票据归其他（真充电由上面的供电/充电服务命中）
        (['生活服务'],                                                      '其他'),
    ]
    for keys, label in rules:
        if any(k in cats for k in keys):
            return label

    # Seller-name fallbacks
    if any(k in seller for k in ['新电途', '众安', '充电']):
        return '充电'
    return '其他'

def check_buyer(text):
    n = re.sub(r'\s+', '', text)
    name_ok = BUYER_NAME.replace(' ', '') in n
    tax_ok  = BUYER_TAX in text or BUYER_TAX in n
    return name_ok, tax_ok

def sanitize(s):
    return re.sub(r'[\\/:*?"<>|]', '_', s)

used = {}
def unique(base, ext='.pdf'):
    name = base + ext
    if name not in used:
        used[name] = 1; return name
    used[name] += 1
    return f"{base}_{used[name]}{ext}"

# Pre-load stable filenames (already renamed, not temp)
for f in os.listdir(OUT_DIR):
    if not f.startswith('_'):
        used[f] = 1

# ── Process all PDFs (including _tmp_* and _new_* files) ─────────────────

pdfs = [os.path.join(OUT_DIR, f) for f in os.listdir(OUT_DIR)
        if f.endswith('.pdf')]

issues = []
print(f"Processing {len(pdfs)} PDF files...")

for path in sorted(pdfs):
    fname = os.path.basename(path)
    try:
        text = read_pdf(path)
    except Exception as e:
        print(f"  [ERROR] Cannot read {fname}: {e}")
        continue

    amount = get_amount(text)
    if not amount:
        amount = "未知金额"
        issues.append(f"金额未提取: {fname}")

    seller   = get_seller(text)
    category = get_category(text, seller)

    name_ok, tax_ok = check_buyer(text)
    if not name_ok or not tax_ok:
        issues.append(f"抬头异常: {fname} → {category}_{amount} "
                      f"(名称:{'✓' if name_ok else '✗'} 税号:{'✓' if tax_ok else '✗'})")

    new_name = unique(sanitize(f"{category}_{amount}"))
    new_path = os.path.join(OUT_DIR, new_name)
    if path != new_path:
        if os.path.exists(new_path):
            os.remove(new_path)
        os.rename(path, new_path)
    print(f"  {fname[:45]:45s} → {new_name}")

print()
if issues:
    print("=== 问题汇总 ===")
    for iss in issues:
        print(f"  ⚠  {iss}")
else:
    print("=== 无异常 ===")
