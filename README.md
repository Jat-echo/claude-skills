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

### [`/knowledge-card`](./knowledge-card/knowledge-card.md) — 知识卡片生成

Extracts the core theme, logical structure, and key insight from any long-form content (articles, book notes, essays), then generates a Morandi-style knowledge card image using the current client's native image generation (Claude Code, Codex, ChatGPT, Gemini).

**Steps:**
1. Deep extraction — structured three-part summary: Theme / Structure / Insight
2. Format card copy — title, bullet points, insight, source tag
3. Generate image — prompt sent to current client's built-in image tool (no API key needed)

**Register:**
```bash
# macOS / Linux
curl -o ~/.claude/commands/knowledge-card.md \
  "https://raw.githubusercontent.com/Jat-echo/claude-skills/main/knowledge-card/knowledge-card.md"
```
```powershell
# Windows
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Jat-echo/claude-skills/main/knowledge-card/knowledge-card.md" `
  -OutFile "$env:USERPROFILE\.claude\commands\knowledge-card.md"
```

---

## Adding a New Skill

1. Create a subdirectory: `mkdir <skill-name>`
2. Add a `<skill-name>.md` describing the workflow (this becomes the slash command)
3. Add any supporting scripts alongside it
4. Update this README with a summary entry
5. Register locally: copy the `.md` to `~/.claude/commands/`
