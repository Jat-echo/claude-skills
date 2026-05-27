# -*- coding: utf-8 -*-
"""
Step 1: Download invoices from Feishu mail 发票 folder.
Usage: python invoice_download.py <OUT_DIR> [<YEAR_MONTH>]
  OUT_DIR     e.g. D:\Work\Uah\办公\报销\202605
  YEAR_MONTH  e.g. 202605  (optional filter; omit to download all)
"""
import sys, os, re, json, subprocess, html, zipfile, io
sys.stdout.reconfigure(encoding='utf-8')

LARK   = r"C:\Users\Administrator\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\npm\lark-cli.cmd"
PY39   = r"D:\Software\Python\Python39\python.exe"
env    = os.environ.copy()
env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else r"D:\Work\Uah\办公\报销\202605"
os.makedirs(OUT_DIR, exist_ok=True)

# ── lark helpers ──────────────────────────────────────────────────────────

def run_lark(args):
    r = subprocess.run([LARK] + args, capture_output=True, env=env)
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
    subprocess.run([PY39, "-c", code], capture_output=True)
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
out = run_lark(['mail', 'user_mailbox.message', 'list',
                '--params', json.dumps({"user_mailbox_id": "me", "folder_key": "inbox",
                                        "page_size": 50})])
# NOTE: adjust folder_key for your 发票 folder; use lark-cli mail to explore folders first.
# Default uses inbox. Run: lark-cli mail user_mailbox.folder list --params '{"user_mailbox_id":"me"}'

try:
    messages = json.loads(out).get('data', {}).get('items', [])
except Exception as e:
    print(f"[ERROR] Cannot list emails: {e}")
    sys.exit(1)

print(f"Found {len(messages)} messages")

results = []
for i, msg in enumerate(messages):
    msg_id  = msg.get('message_id', '')
    subject = msg.get('subject', '') or ''
    print(f"\n[{i+1}/{len(messages)}] {subject[:60]}")

    # Fetch full message
    out = run_lark(['mail', '+message', '--message-id', msg_id, '--format', 'json'])
    try:
        data = json.loads(out).get('data', {})
    except:
        continue

    body_html   = data.get('body_html', '') or ''
    attachments = data.get('attachments', []) or []

    pdf_data = None
    hint     = subject

    # ── A: PDF attachments ───────────────────────────────────────────────
    pdf_atts = [a for a in attachments
                if a.get('content_type', '') == 'application/pdf'
                or (a.get('filename', '') or '').lower().endswith('.pdf')]
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
