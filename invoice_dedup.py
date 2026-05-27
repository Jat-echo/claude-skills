# -*- coding: utf-8 -*-
"""
Step 3: Remove exact duplicate PDFs (same MD5 hash), keep one copy.
Usage: python invoice_dedup.py <OUT_DIR>
"""
import sys, os, hashlib
sys.stdout.reconfigure(encoding='utf-8')

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else r"D:\Work\Uah\办公\报销\202605"

def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

seen = {}
deleted = 0
for fname in sorted(os.listdir(OUT_DIR)):
    if not fname.endswith('.pdf') or fname.startswith('_'):
        continue
    path = os.path.join(OUT_DIR, fname)
    h = md5(path)
    if h in seen:
        os.remove(path)
        print(f"  删除重复: {fname}  (同: {seen[h]})")
        deleted += 1
    else:
        seen[h] = fname

print(f"\n共删除 {deleted} 个重复文件，剩余 {len(seen)} 张")
