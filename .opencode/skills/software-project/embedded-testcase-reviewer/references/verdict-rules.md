# Verdict Rules

Use only these verdicts:

- `Implemented`
- `Not Implemented`
- `Uncertain`

## Implemented

Use `Implemented` only when all of the following are true:

1. The testcase preconditions are representable in the reviewed codebase.
2. The trigger path can be traced from an entry point to the final observable behavior.
3. The expected behavior matches the actual branch, state machine result, or hardware-facing output.
4. No missing repository boundary, model selection, or compile-time variant is required to justify the conclusion.

Typical evidence pattern:

1. Entry function or event source
2. State variables updated
3. Decision branch or state-machine case
4. Final output API or cross-chip command

Do not use `Implemented` when you only found:

- a matching enum or macro but no caller
- a state variable update with no output path
- a likely path in one model while the target model is unknown

## Not Implemented

Use `Not Implemented` when one of these is proven:

1. The required branch or state transition does not exist.
2. The visible output conflicts with the testcase expectation.
3. The state exists but is never connected to the final hardware-facing behavior.
4. A required event updates internal state, but no refresh path or output path is wired.
5. The implementation covers a different product variant and the current target path clearly lacks the behavior.

Typical evidence pattern:

1. Show where the expected state would need to be checked
2. Show that the code does not check it, or checks it differently
3. Show the actual output path that produces a conflicting behavior

Good `Not Implemented` cases:

- testcase requires charging LED behavior, but the active LED state machine never reads charging state
- testcase requires upgrade red/blue alternating blink, but the code only produces red blink or blue animation
- testcase requires transition on plug/unplug event, but the event handler never refreshes the output

## Uncertain

Use `Uncertain` only when a decisive answer depends on missing information.

Valid reasons include:

1. Target model or board type is unknown and variant code differs
2. Required compile-time macro or capability-set selection is unknown
3. Expected behavior may be implemented in bootloader, loader, or MCU firmware not present in the workspace
4. Runtime configuration or flash-stored option is required and its value is not known
5. The testcase explicitly targets hardware or firmware outside the reviewed repository boundary

`Uncertain` must always include a `Missing Information` section that states exactly what is needed.

Do not use `Uncertain` for these cases:

- you have not yet traced the obvious code path
- the code clearly conflicts with the testcase
- the code clearly lacks the required state/output connection

## Evidence Requirements

Every verdict must cite:

1. At least one concrete file
2. At least one concrete function or decision point
3. The key state variable, macro, or message involved
4. A short call-chain or state-flow summary

The evidence should answer: why is this verdict justified in code?

## Variant Handling Rules

When the codebase has generic and model-specific paths:

1. Search both generic and specialized paths before deciding
2. If the testcase target model is known, prioritize that model's path
3. If the target model is unknown and variants diverge, use `Uncertain`
4. If the target model is known and the active variant clearly lacks the behavior, use `Not Implemented`

## Cross-Repository Boundary Rules

If the visible behavior may live in another repository or firmware image:

1. State the boundary explicitly: AP app, MCU firmware, bootloader, codec, or vendor library
2. Report what the current repository does provide
3. If the missing boundary is required to prove the testcase, use `Uncertain`

## Severity Summary for Systemic Issues

After per-testcase verdicts, summarize systemic issues as:

- `High`: causes a full testcase group or critical customer flow to fail
- `Medium`: affects a subset of cases or a secondary path
- `Low`: evidence gap, maintainability issue, or non-blocking inconsistency