# Output Template

Use this structure unless the user asks for a different format.

Default file target: `testcase_review.md` at the repository root.

Start the file with:

```markdown
# Testcase Review

## Scope
- Testcase source: [path or description]
- Code scope: [reviewed folders or files]
- Product / model: [if known]
- Active macro / capability assumptions: [if known]

## Assumptions
- [assumption 1]
- [assumption 2]
```

## Per-Testcase Verdict

```markdown
### Testcase [ID or Name]

**Verdict:** Implemented | Not Implemented | Uncertain

**Why:**
[1-3 concise sentences explaining the conclusion]

**Evidence:**
- Entry: [event, function, or callback]
- State: [key variable, flag, bitmap, config, or message]
- Decision: [branch, state-machine case, or macro-gated logic]
- Output: [GPIO write, inter-chip message, peripheral command, persisted flag, etc.]
- Code: [file + function references]

**Missing Information:**
[Only for Uncertain. State exactly what information is needed.]

**Note:**
[Optional short risk or variant note]
```

## Systemic Issues Summary

After the per-testcase verdicts, add:

```markdown
## Issues

### High
- [Systemic issue that breaks a testcase group]

### Medium
- [Partial or variant-specific issue]

### Low
- [Evidence gap, maintainability risk, or inconsistent implementation]
```

## Short-Form Table Option

If the user wants a compact summary first, use:

```markdown
| Testcase | Verdict | Key Evidence | Missing Info |
|----------|---------|--------------|--------------|
| TC-001 | Implemented | `foo()` -> state `bar` -> GPIO set in `baz()` | - |
| TC-002 | Not Implemented | no branch checks `charging_state` in active LED path | - |
| TC-003 | Uncertain | output may be owned by MCU firmware, not current repo | target MCU repo / protocol owner |
```

Then expand only the non-trivial cases below the table.

## Writing Rules

1. Keep `Why` short and factual.
2. Put proof in `Evidence`, not in vague prose.
3. For `Uncertain`, name the missing condition explicitly.
4. Do not say "probably implemented" or "seems missing". Choose one of the three verdicts.
5. If several testcases fail for the same root cause, repeat concise testcase-level evidence and group the root cause in the final issue summary.
6. Unless the user asks for chat-only output, persist the full review into `testcase_review.md`.