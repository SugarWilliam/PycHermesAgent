---
name: embedded-testcase-reviewer
description: >
  Review embedded product code against testcases and return a verdict for each
  testcase: Implemented, Not Implemented, or Uncertain with concrete code
  evidence. Use this skill when: (1) the user provides Markdown or text testcases
  and asks whether each testcase is implemented in code; (2) the target is an
  embedded Linux or FreeRTOS product with peripherals such as GPIO, I2C, UART,
  SPI, SDIO, or USB; (3) the codebase may involve multiple chips or firmware
  boundaries such as AP, MCU, codec, sensor, bootloader, or power controller;
  (4) different ARM platforms, board types, models, feature sets, or macros may
  change behavior; (5) the user asks for testcase review, testcase-to-code
  mapping, per-case implementation verdict, 缺少条件不确定, 根据测试用例查代码,
  测试用例评审, 逐条用例核对, 是否实现, or 代码是否覆盖测试用例.
---

# Embedded Testcase Reviewer

Review embedded product code against explicit testcases and produce a verdict for each testcase:

- `Implemented`
- `Not Implemented`
- `Uncertain`

Every verdict must include code evidence.

This skill is for static code review, not board-level execution.

## Hard Rule: No Guessing

If critical information is missing, you must ask for it before claiming a testcase is implemented.

Do not guess across these boundaries:

- product model or board type
- compile-time macros or capability-set selection
- external MCU or secondary-chip firmware behavior
- bootloader or upgrade-loader behavior
- code that is not present in the current workspace
- runtime configuration stored in flash, NVRAM, or server-side config

If one of these boundaries is required to decide the testcase, the verdict must be `Uncertain` until the missing information is provided.

Before producing verdicts, read:

- [references/verdict-rules.md](references/verdict-rules.md)
- [references/embedded-trace-checklist.md](references/embedded-trace-checklist.md)
- [references/output-template.md](references/output-template.md)

## Required Inputs

Minimum useful input:

1. Testcase document in Markdown or plain text
2. Code scope to review

Strongly preferred input:

1. Target product or model
2. Relevant build macros, capability-set, or board-type selection
3. Whether behavior is owned by AP code, MCU firmware, bootloader, or another repository

If the testcase depends on any of the preferred inputs and they are missing, ask for them.

## Workflow

### Phase 1: Clarify Scope Before Reviewing

Confirm these points first:

1. Which product or model is under review?
2. Which codebase is authoritative for the feature: AP, MCU, bootloader, or another component?
3. Are there compile-time macros, board types, or capability sets that change behavior?
4. Is the testcase meant for all models or only a subset?

If the answer is unknown and the distinction matters, stop and ask.

### Phase 2: Normalize Each Testcase

For each testcase, extract:

1. Testcase ID or name
2. Preconditions
3. Trigger or user action
4. Expected result
5. Any hidden product assumptions, such as charging mode, upgrade phase, standby vs running, AP/MCU split, or specific peripheral path

If a single testcase contains multiple expected behaviors, split it into sub-observations during analysis, but report under the original testcase.

### Phase 3: Map Testcase to Code

Trace the complete path:

1. Entry event
2. State update
3. State machine or branch decision
4. Cross-chip message or callback if present
5. Hardware-facing output such as GPIO, I2C command, UART message, SPI transaction, SDIO path, USB action, or persisted flag

Do not stop at a variable assignment. Follow the path to the actual visible behavior.

Use [references/embedded-trace-checklist.md](references/embedded-trace-checklist.md) while tracing.

### Phase 4: Decide the Verdict

Use only the three allowed verdicts:

- `Implemented`: The code path exists and reaches the expected observable behavior under the testcase conditions.
- `Not Implemented`: The code lacks the necessary branch, state, output, or integration point, or clearly implements conflicting behavior.
- `Uncertain`: The answer depends on missing information outside the available evidence.

Use the stricter definitions in [references/verdict-rules.md](references/verdict-rules.md).

### Phase 5: Produce Output

For every testcase, output a verdict with evidence using [references/output-template.md](references/output-template.md).

Also provide a short issue list ordered by severity. This list should group systemic problems that cause many testcase failures.

Unless the user explicitly asks for a different target, write the full review result to a repository-root Markdown file named `testcase_review.md`.

The file should contain:

1. Review scope and assumptions
2. Per-testcase verdicts
3. Missing-information notes for uncertain cases
4. Severity-ordered systemic issues

If a `testcase_review.md` file already exists, update it instead of creating a parallel file with a different name unless the user asks otherwise.

## Embedded Review Focus

Always account for these embedded-specific dimensions:

- Linux threads, event loops, RPC, daemons, kernel/user-space boundaries
- FreeRTOS tasks, timers, queues, callbacks, ISR-triggered state updates
- peripheral IO through GPIO, I2C, UART, SPI, SDIO, USB
- multi-chip interaction between AP, MCU, codec, PMIC, charger, or sensor controllers
- model differences controlled by macros, board types, feature flags, capability sets, or persisted config
- behavior split across normal app, bootloader, upgrade-loader, and external firmware

## Review Discipline

1. Never mark `Implemented` based on a partial pattern match.
2. Never mark `Not Implemented` until you have searched the relevant variant paths.
3. Never use `Uncertain` as a shortcut for incomplete analysis.
4. If a testcase spans a missing repository boundary, say so explicitly.
5. If two product variants implement different behavior, report that divergence explicitly instead of averaging them together.

## When to Ask Follow-up Questions

Ask before continuing when any of these materially affects the verdict:

- the testcase applies only to a subset of models
- a macro or capability set likely changes the path
- the visible behavior may be owned by MCU or bootloader code not in the workspace
- the testcase expectation conflicts with the visible code and may depend on another repository
- the codebase contains both generic and model-specific implementations and the target is unspecified

## Final Deliverable

Default deliverable:

1. Per-testcase verdict table or list
2. Evidence for each testcase
3. Missing-information note for each `Uncertain` verdict
4. Severity-ordered systemic issue list
5. Write the result into `testcase_review.md` at the repository root by default

Do not rewrite the testcase document unless the user asks.