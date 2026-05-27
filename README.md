# Claude Skills

Personal collection of reusable Claude Code slash command skills.

Each skill lives in its own subdirectory and can be registered as a `/command` in Claude Code by copying the `.md` file to `~/.claude/commands/`.

---

## Skills

### [`/invoice`](./invoice/invoice.md) — 发票整理

Automatically downloads all invoices from the Feishu mailbox "发票" folder, renames them by category and tax-inclusive amount, and deduplicates by MD5 hash.

**Steps:**
1. `invoice_download.py` — Download PDFs via lark-cli (PDF attachments → ZIP → body links → 百旺 SPA placeholder)
2. `invoice_rename.py` — Classify by item content and rename to `{类别}_{金额}.pdf`
3. `invoice_dedup.py` — Remove exact duplicates (MD5)

**Register:**
```powershell
Copy-Item "invoice\invoice.md" "$env:USERPROFILE\.claude\commands\invoice.md"
```

---

## Adding a New Skill

1. Create a subdirectory: `mkdir <skill-name>`
2. Add a `<skill-name>.md` describing the workflow (this becomes the slash command)
3. Add any supporting scripts alongside it
4. Update this README with a summary entry
5. Register locally: copy the `.md` to `~/.claude/commands/`
