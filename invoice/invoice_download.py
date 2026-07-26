# -*- coding: utf-8 -*-
r"""
Step 1: Download invoices from Feishu mail 发票 folder.
Usage: python invoice_download.py <OUT_DIR> [<YEAR_MONTH>]
  OUT_DIR     e.g. D:\Work\Uah\办公\报销\202605
  YEAR_MONTH  e.g. 202605  (optional filter; omit to download all)
"""
import sys, os, re, json, subprocess, html, zipfile, io
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

# 直连 opener（不走本地代理），用于诺诺等国内发票平台
_noproxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

LARK   = r"C:\Users\Administrator\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\npm\lark-cli.cmd"
PY39   = r"D:\Software\Python\Python39\python.exe"
env    = os.environ.copy()
env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")
env["LARK_CLI_NO_PROXY"] = "1"          # mail API 走直连，避免本地代理干扰

# 下载附件用的环境：去掉代理，飞书 drive 直连即可
dl_env = os.environ.copy()
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    dl_env.pop(_k, None)

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else r"D:\Work\Uah\办公\报销\202605"
os.makedirs(OUT_DIR, exist_ok=True)

# ── lark helpers ──────────────────────────────────────────────────────────

def run_lark(args):
    # 所有邮件命令必须以用户身份调用
    r = subprocess.run([LARK] + args + ['--as', 'user'], capture_output=True, env=env)
    return r.stdout.decode('utf-8-sig', errors='replace')

def get_att_url(msg_id, att_id):
    out = run_lark(['mail', 'user_mailbox.message.attachments', 'download_url',
                    '--params', json.dumps({"user_mailbox_id": "me",
                                            "message_id": msg_id,
                                            "attachment_ids": [att_id]})])
    try:
        urls = json.loads(out).get('data', {}).get('download_urls', [])
        return urls[0].get('download_url') if urls else None
    except:
        return None

def download(url, out_path):
    """Download via Python39 which has working urllib/proxy."""
    url_safe = url.encode('ascii', errors='ignore').decode('ascii')
    code = (
        "import urllib.request; "
        f"req=urllib.request.Request({repr(url_safe)},headers={{'User-Agent':'Mozilla/5.0'}});"
        f"resp=urllib.request.urlopen(req,timeout=30);"
        f"open({repr(out_path)},'wb').write(resp.read())"
    )
    subprocess.run([PY39, "-c", code], capture_output=True, env=dl_env)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None
    with open(out_path, 'rb') as f:
        return f.read()

# ── URL extraction helpers ────────────────────────────────────────────────

def extract_pdf_links(html_body):
    links = []
    decoded = html.unescape(html_body)
    for url in re.findall(r'https?://[^\s"\'<>]+', decoded):
        if re.search(r'\.pdf|dzfp|einvoice|fapiao|fp_|invoice|download', url, re.IGNORECASE):
            if not re.search(r'track|pixel|logo|img|gif|png|jpg|banner|open\?', url, re.IGNORECASE):
                if url not in links:
                    links.append(url)
    return links

def extract_nuonuo_links(html_body):
    """从正文提取诺诺发票(jss.com.cn)短链，如 https://nnfp.jss.com.cn/<code>。"""
    decoded = html.unescape(html_body)
    out = []
    for u in re.findall(r'https?://nnfp\.jss\.com\.cn/[^\s"\'<>]+', decoded):
        p = urllib.parse.urlparse(u)
        seg = p.path.strip('/')
        if '/' in seg:
            # 已是 printQrcode?paramList=... 之类，保留带 paramList 的
            if 'paramList' in (p.query or '') and u not in out:
                out.append(u)
            continue
        # 单段短码链接；排除接口/资源路径
        if seg and not seg.startswith(('allow', 'sapi', 'scan-invoice', 'nnwzf', 'nnww')):
            if u not in out:
                out.append(u)
    return out

def get_nuonuo_pdf(url):
    """诺诺发票：短链→paramList→明细接口→PDF 直链。返回 pdf_url 或 None。"""
    try:
        final = _noproxy_opener.open(
            urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}),
            timeout=30).geturl()
        param = urllib.parse.parse_qs(urllib.parse.urlparse(final).query).get('paramList', [None])[0]
        if not param:
            return None
        data = ('paramList=' + urllib.parse.quote(param, safe='')).encode()
        req = urllib.request.Request(
            'https://nnfp.jss.com.cn/sapi/scan2/getIvcDetailShow.do', data=data,
            headers={'User-Agent': 'Mozilla/5.0',
                     'Content-Type': 'application/x-www-form-urlencoded', 'Referer': final})
        j = json.loads(_noproxy_opener.open(req, timeout=30).read().decode('utf-8'))
        return j.get('data', {}).get('invoiceSimpleVo', {}).get('url')
    except Exception as e:
        print(f"  [WARN] 诺诺解析失败: {e}")
        return None

def sanitize(s):
    return re.sub(r'[\\/:*?"<>|]', '_', s)

used_names = {}
def unique(base, ext='.pdf'):
    name = base + ext
    if name not in used_names:
        used_names[name] = 1; return name
    used_names[name] += 1
    return f"{base}_{used_names[name]}{ext}"

# Pre-load existing filenames
for f in os.listdir(OUT_DIR):
    used_names[f] = 1

# ── List emails in 发票 folder ────────────────────────────────────────────

print("Listing 发票 folder...")

# 1) 按名称找到「发票」文件夹 id
fout = run_lark(['mail', 'user_mailbox.folders', 'list',
                 '--params', json.dumps({"user_mailbox_id": "me"})])
folder_id = None
try:
    for f in json.loads(fout).get('data', {}).get('items', []):
        if f.get('name') == '发票':
            folder_id = f.get('id'); break
except Exception as e:
    print(f"[ERROR] 文件夹列取失败: {e}\n{fout[:300]}")
    sys.exit(1)
if not folder_id:
    print("[ERROR] 未找到「发票」文件夹")
    sys.exit(1)

# 2) 列出该文件夹全部邮件（page_size 上限 20，自动翻页）；返回的 items 是 message_id 字符串数组
out = run_lark(['mail', 'user_mailbox.messages', 'list',
                '--params', json.dumps({"user_mailbox_id": "me",
                                        "folder_id": folder_id, "page_size": 20}),
                '--page-all', '--page-limit', '50'])

try:
    messages = json.loads(out).get('data', {}).get('items', [])
except Exception as e:
    print(f"[ERROR] Cannot list emails: {e}\n{out[:300]}")
    sys.exit(1)

print(f"Found {len(messages)} messages")

results = []
for i, msg in enumerate(messages):
    msg_id  = msg if isinstance(msg, str) else (msg.get('message_id', '') or '')
    if not msg_id:
        continue

    # Fetch full message
    out = run_lark(['mail', '+message', '--message-id', msg_id, '--format', 'json'])
    try:
        data = json.loads(out).get('data', {})
    except:
        continue

    subject = data.get('subject', '') or ''
    print(f"\n[{i+1}/{len(messages)}] {subject[:60]}")

    body_html   = data.get('body_html', '') or ''
    attachments = data.get('attachments', []) or []

    pdf_data = None
    hint     = subject

    # ── A: PDF attachments ───────────────────────────────────────────────
    # 通行费邮件常同时带 ZIP(真发票) 和 松散的「票据/行程/汇总单」PDF；
    # 后者不是增值税发票，须跳过，交给 Step B 从 ZIP 里取真发票。
    _SKIP_PDF_KW = ('票据', '行程', '汇总单', '清单')
    pdf_atts = [a for a in attachments
                if (a.get('content_type', '') == 'application/pdf'
                    or (a.get('filename', '') or '').lower().endswith('.pdf'))
                and not any(kw in (a.get('filename', '') or '') for kw in _SKIP_PDF_KW)]
    for att in pdf_atts:
        att_id = att.get('id') or att.get('attachment_id')
        if not att_id: continue
        url = get_att_url(msg_id, att_id)
        if not url: continue
        tmp = os.path.join(OUT_DIR, f"_tmp_{i}.pdf")
        pdf_data = download(url, tmp)
        if pdf_data and len(pdf_data) > 1000:
            print(f"  [OK] PDF attachment ({len(pdf_data)//1024}KB)")
            break
        pdf_data = None

    # ── B: ZIP attachments (通行费电子发票.zip) ──────────────────────────
    if not pdf_data:
        zip_atts = [a for a in attachments
                    if (a.get('filename', '') or '').lower().endswith('.zip')]
        for att in zip_atts:
            att_id = att.get('id') or att.get('attachment_id')
            if not att_id: continue
            fname  = att.get('filename', '')
            # Skip 票据 ZIPs; only take 发票 ZIPs
            if '票据' in fname and '发票' not in fname:
                print(f"  [SKIP] 票据 ZIP: {fname}")
                continue
            url = get_att_url(msg_id, att_id)
            if not url: continue
            tmp_zip = os.path.join(OUT_DIR, f"_tmp_{i}.zip")
            zip_data = download(url, tmp_zip)
            if not zip_data: continue
            try:
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    # Only extract files from pdf/ subdirectory
                    pdf_entries = [n for n in zf.namelist()
                                   if n.startswith('pdf/') and n.lower().endswith('.pdf')]
                    for j, name in enumerate(pdf_entries):
                        entry_data = zf.read(name)
                        if len(entry_data) < 1000: continue
                        tmp = os.path.join(OUT_DIR, f"_tmp_{i}_{j}.pdf")
                        with open(tmp, 'wb') as f2:
                            f2.write(entry_data)
                        results.append({'path': tmp, 'hint': hint + f'_zip{j}'})
                        print(f"  [ZIP] Extracted: {name} ({len(entry_data)//1024}KB)")
            except Exception as e:
                print(f"  [WARN] ZIP error: {e}")
            try: os.remove(tmp_zip)
            except: pass
            continue  # handled via results list

    # ── C: PDF links in email body ───────────────────────────────────────
    if not pdf_data:
        for link in extract_pdf_links(body_html)[:5]:
            tmp = os.path.join(OUT_DIR, f"_tmp_{i}.pdf")
            pdf_data = download(link, tmp)
            if pdf_data and len(pdf_data) > 1000 and pdf_data[:4] == b'%PDF':
                print(f"  [OK] Link download ({len(pdf_data)//1024}KB)")
                break
            pdf_data = None

    # ── C2: 诺诺发票 (jss.com.cn) SPA 短链 → 走接口取 PDF 直链 ───────────
    if not pdf_data:
        for nlink in extract_nuonuo_links(body_html):
            pdf_url = get_nuonuo_pdf(nlink)
            if not pdf_url:
                continue
            tmp = os.path.join(OUT_DIR, f"_tmp_{i}.pdf")
            pdf_data = download(pdf_url, tmp)
            if pdf_data and len(pdf_data) > 1000 and pdf_data[:4] == b'%PDF':
                print(f"  [OK] 诺诺发票 ({len(pdf_data)//1024}KB)")
                break
            pdf_data = None

    # ── D: 百旺/SPA pages → log URL for manual/browser download ─────────
    if not pdf_data:
        spa_links = [u for u in extract_pdf_links(body_html)
                     if 'baiwang.com' in u or 'smkp-vue' in u]
        if spa_links:
            print(f"  [SPA] 百旺发票，需浏览器下载: {spa_links[0][:80]}")
            # Save a placeholder
            placeholder = os.path.join(OUT_DIR, f"_SPA_{sanitize(subject)}.url.txt")
            with open(placeholder, 'w', encoding='utf-8') as f2:
                f2.write(spa_links[0])
        else:
            print("  [SKIP] No PDF found")
        continue

    if pdf_data:
        results.append({'path': os.path.join(OUT_DIR, f"_tmp_{i}.pdf"), 'hint': hint})

print(f"\nDownloaded {len(results)} PDF files (before rename)")
