# Writing SOP: prose conventions for anything new on the site

> 适用：全站新写的内容，包括 blog 正文、`news.html` / `work.html` 条目、timeline、hero 与 meta
> 文案、commit message，以及 EN 与 ZH 两侧。姊妹文档：`ZH-TRANSLATION-SOP.md`（中文用词）、
> `OG-CARD-SOP.md`（社交卡片）。

## Rule 1: no em dash. Ever.

Do not write `—` (U+2014), `&mdash;`, `&#8212;`, or the Chinese `——`.

This is absolute for new content. It is the single most recognisable tell of
machine-written prose, and this site is read by people who know the tell. The
cost of the rule is nothing: every em dash is a decision the writer declined to
make, and one of the replacements below is always sharper.

### What to write instead

| Job the em dash was doing | Use | Example |
|---|---|---|
| Introducing a list or an explanation | colon | `Three labs converged: Google, DeepSeek, Z.ai.` |
| Joining two independent clauses | full stop, or semicolon if truly paired | `The gap is not hypocrisy. It is physics.` |
| Wrapping an aside | commas, or parentheses if the aside is a genuine footnote | `Bedrock, then two months old, had no Claude support.` |
| Appending a qualifier or a result | comma | `Open weights two weeks out, after safety evaluation.` |
| Attributing a quote | `by`, or put the name on its own line | `by Matt Garman, AWS CEO` |
| Numeric range | en dash `–` stays legal | `2023–Present`, `pp. 14–18` |

The en dash (`–`, U+2013) is **only** for ranges between numbers or dates. Never
use it as a substitute em dash in prose: swapping one dash for a narrower dash
keeps the habit and fools nobody.

### ZH side

Chinese prose normally takes `——`, and roughly 3,000 of them are already on this
site. New Chinese content still does not use it. Reach for `，` `：` `（）` or a
full stop instead:

| ❌ | ✅ |
|---|---|
| `Z.ai 发布 GLM-5.3——只做后训练` | `Z.ai 发布 GLM-5.3，只做后训练` |
| `对比 Fable 5：CyberGym 反超——ExploitBench 落后` | `对比 Fable 5：CyberGym 反超，ExploitBench 落后。` |

Everything else in `ZH-TRANSLATION-SOP.md` (全角标点、中英文之间空格) still applies.

## Scope: new content only

The rule starts 2026-08-14 and is not retroactive. The 3,288 existing instances
stay: rewriting a decade of posts would churn every page for a habit that only
matters going forward, and the older essays have their own settled voice.

One exception, so the rule actually takes hold: if you are already editing a
sentence for other reasons, fix its dashes on the way past.

## Check before committing

```bash
# added lines in the working tree / staged diff that introduce a dash
python3 scripts/check_dashes.py

# a specific file, whole-file scan (expect legacy hits on old posts)
python3 scripts/check_dashes.py --files blog/2026/newpost/index.html
```

`check_dashes.py` reads the diff against `HEAD` plus any untracked file, so it
only ever complains about lines you are adding. A clean run is the gate: it exits
non-zero if a new line carries an em dash in any of its four spellings.

Two escape hatches. This SOP and `check_dashes.py` are skipped wholesale, since
defining the rule means spelling out the characters it bans. And a line carrying
the token `dash-ok` is exempt, for verbatim quotation only: repunctuating a
source you are quoting is a misquote, so quote it as written and mark the line.

## Checklist

- [ ] No `—`, `&mdash;`, `&#8212;`, `——` in anything added
- [ ] `–` appears only between numbers or dates
- [ ] Replacements read as deliberate punctuation, not as a dash swapped for a comma
- [ ] EN and ZH siblings both clean (`ZH-TRANSLATION-SOP.md` checklist also passed)
- [ ] `python3 scripts/check_dashes.py` exits clean
