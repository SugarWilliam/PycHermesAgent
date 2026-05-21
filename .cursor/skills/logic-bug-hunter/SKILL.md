---
name: logic-bug-hunter
description: >
  Deep logic bug analysis for C/C++ applications. Given bug description,
  expected behavior, and logs, performs context expansion, call-chain tracing,
  cross-module data flow analysis, and state machine verification to pinpoint
  root causes of deterministic and intermittent bugs. Specializes in logic
  errors and requirement-implementation mismatches. Use when: (1) user describes
  a bug with symptom + expected behavior; (2) user provides logs to narrow
  incorrect behavior; (3) logic errors, wrong output, wrong state transitions;
  (4) intermittent/sporadic hard-to-reproduce bugs; (5) keywords: "逻辑错误",
  "逻辑bug", "需求不对", "实现不对", "行为不符合预期", "偶现bug", "必现bug",
  "logic bug", "wrong behavior", "intermittent", "requirement mismatch",
  "root cause"; (6) code + expected vs actual behavior analysis.
---

# Logic Bug Hunter

Deep logic bug analysis: given symptoms, expectations, and logs, trace through code context, call chains, cross-module interactions, and state machines to find root causes of both deterministic and intermittent logic bugs.

## Input Collection

| Input | Required | Purpose |
|-------|----------|---------|
| **Bug Description** | Yes | What actually happens — the incorrect behavior |
| **Expected Result** | Yes | What should happen — correct behavior per requirement |
| **Runtime Logs** | On-Demand | Needed to resolve ambiguity; skip if 100% deducible statically |
| **Relevant Code** | Recommended | Source files/functions suspected to be involved |
| **Reproduction Steps** | Optional | How to trigger (always? specific sequence? timing?) |
| **Requirement Doc** | Optional | Bridges gap between code and intent |

If **Bug Description** or **Expected Result** is missing, ask before proceeding.

---

## The Iron Law

```
NO FIX PROPOSALS BEFORE COMPLETING AT LEAST THROUGH PHASE 6.
SEEING SYMPTOMS ≠ UNDERSTANDING ROOT CAUSE.
```

---

## Analysis Workflow

```
Phase 0: Discipline Gate → Phase 1: Gap Characterization → Phase 2: Log Analysis
→ Phase 3: Hypothesis Formation → Phase 4: Context Expansion & Call-Chain Tracing
→ Phase 5: Logic Simulation → Phase 6: Confidence Evaluation
→ Phase 7: Intermittent Analysis (if applicable) → Phase 8: Root Cause & Fix
```

### Phase 0: Discipline Gate

#### 0a. Reproducibility Gate

- Can the bug be triggered reliably?
- If **not reproducible** → do NOT guess. Ask for more info, or suggest targeted instrumentation (see [debugging_guide.md](references/debugging_guide.md)).
- Only proceed after establishing reproduction steps or sufficient log evidence.

#### 0b. Recent Changes Check

- **Mandatory**: Check SVN/Git diff of last N commits touching related modules, config changes, env differences.
- Recent change in bug's code path → Hypothesis #1 priority.
- Regression ("it used to work") → diff is #1 evidence source.

#### 0c. Working Reference Search

- Find **functionally similar code that works**: similar command handler, same feature on different platform, previous VCS version.
- Keep for comparison in Phase 3.

### Phase 1: Gap Characterization

1. **Define the Behavioral Gap**: what differs, how much, when it appears.

2. **Classify the Bug Nature**:

   | Type | Analysis Focus |
   |------|----------------|
   | **Deterministic** | Algorithmic flow, conditions, calculations |
   | **State-Dependent** | State machine, initialization, residual state |
   | **Intermittent** | Concurrency, timing, uninitialized data |
   | **Requirement Mismatch** | Design intent vs implementation gap |
   | **Boundary / Edge Case** | Boundary conditions, overflow, underflow |
   | **Cross-Module** | Interface contracts, shared state assumptions |
   | **Feature A→B Ripple** | Shared code/state/resource contamination |

3. **Extract Constraints**: specific trigger? scenario where it works? regression vs always-broken? recent Feature A change?

### Phase 2: Log & Print Trace Analysis

#### 2a. Timeline Reconstruction

- Extract timestamps → chronological sequence
- Identify **last correct point** and **first incorrect point**
- Root cause triggers between these two

#### 2b. Variable Value Tracking

- Build variable value timeline from prints
- Find **first divergence** where actual value departs from expected
- Trace backwards between last correct and first wrong print

#### 2c. Control Flow Evidence

| Log Evidence | Deduction |
|-------------|-----------|
| Entry logged, exit NOT | Crash, hang, or unexpected return inside |
| Branch A logged when B expected | Wrong condition — check predicate |
| Same sequence printed twice | Unexpected re-entry, loop error, missing guard |
| Missing expected entry | Code path not reached — check guarding conditions |
| Entries out of order | Race condition, priority inversion |
| Value is 0 / garbage / 0xDEADBEEF | Uninitialized, freed, or not-yet-assigned |
| Correct from A, wrong from B | Bug in B or A→B interface |

#### 2d. Differential Analysis

If logs from both success and failure cases exist: diff → find first divergence → reveals the trigger condition.

### Phase 3: Hypothesis Formation

#### 3a. Working Reference Comparison (from Phase 0c)

Compare broken code vs working reference line by line. Differences correlating with the gap → high-priority hypothesis inputs.

#### 3b. Generate 3-5 Ranked Hypotheses

Priority order for logic bugs:
1. **Recent Change Regression** (Phase 0b)
2. **Requirement-Code Mismatch**
3. **Condition / Branch Error**
4. **State Corruption / Residual State**
5. **Data Flow Corruption**
6. **Timing / Order Dependency**

For each: suspected root cause → code location → verification method → symptom coverage.

**Rule**: Hypotheses explaining ALL symptoms rank higher than partial explanations.

### Phase 4: Deep Context Expansion & Call-Chain Tracing

**Cardinal Rule: Never analyze code in isolation.**

#### 4a. Full Context Expansion (Mandatory)

1. Read **entire suspected function**
2. Read **all related functions** in the same file
3. Read **struct/class definitions** for all types
4. Read **global/static variable** declarations, init, and ALL modification sites
5. Read **macro definitions** — may hide logic or conditional compilation

#### 4b. Upward Tracing (Callers → Suspected Function)

Find ALL callers → what arguments, conditions, expectations → continue to entry point (main dispatch, event handler, timer, thread, IPC handler).

#### 4c. Downward Tracing (Suspected Function → Callees)

Read actual implementation of each callee → preconditions, side effects, error returns → continue to sink (syscall, IPC, storage, global state).

#### 4d. Lateral Tracing (Cross-Module Data Flow)

1. Identify shared state (globals, shared memory, message queues, config)
2. Find ALL other writers and readers
3. Verify: same semantics? synchronization? TOCTOU? field interpretation match?

#### 4e. Feature A→B Ripple Effect Tracing

When bug appeared after another feature was modified:
1. Get exact diff of the other feature's change
2. List shared touchpoints: functions, structs, globals, conditions, resources
3. Trace broken feature's path through each modified touchpoint

See [cross_module_analysis.md](references/cross_module_analysis.md) §6 for full workflow.

#### 4f. Verification Checklist

- Entry point args validated? Each layer transforms correctly?
- Callee preconditions guaranteed? Error returns checked?
- Shared state protocol consistent? Function safe in invocation context?
- Module initialized before use? Type/unit agreement (ms vs s, signed vs unsigned)?

### Phase 5: Logic Simulation & Divergence Detection

With full context, **mentally execute** using the reproduction scenario:

1. Start at entry point with exact inputs
2. At each branch — which path, why? At each assignment — new value? At each call — enter callee.
3. Compare against expected at each step
4. **The line where actual first diverges from expected = root cause location**

**"What If" expansion**: boundary value? silent prior failure? called before init? concurrent state modification? different branch than last time?

### Phase 6: Confidence Evaluation & Iterative Debugging

1. **Confidence Check**: 100% certain about single divergence point causing ALL symptoms?
   - **YES** → Skip to Phase 8
   - **NO** → Step 2. **DO NOT GUESS.**

2. **Iterative Print Debugging**: Pause analysis, ask user to add targeted prints.
   - Generate pinpoint DBG statements based on competing hypotheses
   - Use boundary-narrowing approach — see [debugging_guide.md](references/debugging_guide.md)
   - Output "Required Debug Prints" section and STOP. Wait for new logs.

### Phase 7: Intermittent Bug Analysis

For bugs that don't always reproduce. See [intermittent_bug_patterns.md](references/intermittent_bug_patterns.md) for comprehensive patterns.

**Key principle**: Intermittent bugs are deterministic bugs with hidden preconditions. Find the precondition.

1. **Variable Factor**: timing? state? data? resources?
2. **Race Condition**: shared state → concurrent accessors → race window → losing schedule
3. **Residual State**: prior operation left invalid state? `static` vars, caches, state machines not reset?
4. **Environment Sensitivity**: timing-sensitive ops? load-dependent? specific data patterns?

### Phase 8: Root Cause Confirmation & Fix

1. **Root Cause**: exact location, defective code, mechanism, symptom explanation, trigger condition
2. **Fix**: minimal corrective change, rationale, side effects
3. **Verification**: test to confirm, edge cases, stress test for intermittent bugs
4. **Failure Escalation**:
   - Attempt 1-2 failed → return to Phase 3 (failure is evidence)
   - Attempt ≥3 failed → **STOP. Question architecture.** Signs: each fix reveals new coupling, requires massive refactoring, or creates new symptoms. **Discuss with user** before further attempts.

---

## Report Format

Use templates in [report_template.md](references/report_template.md):
- **Format A**: Debugging Required — when confidence < 100%, output required prints and stop
- **Format B**: Full Analysis Report — when logic loop is 100% closed

---

## Red Flags — STOP and Return to Phase 0

| Red Flag Thought | What's Wrong |
|-----------------|-------------|
| "I see the problem, let me fix it" | Symptoms ≠ root cause. Complete Phase 5 first. |
| "It's probably X, let me just try" | "Probably" = guessing. Evidence in Phase 3. |
| "I've traced so much, it must be here" | Sunk cost ≠ confidence. ALL symptoms explained? |
| "Let me fix multiple things at once" | Can't isolate what worked. One change at a time. |
| "One more fix attempt" (after 2+ fails) | 3+ failures = architectural problem. Phase 8 escalation. |
| "Not reproducible, but I think I know" | No reproduction = no evidence. Phase 0a gate. |
| Proposing fixes before Phase 6 | The Iron Law. No shortcuts. |

---

## References

- [logic_bug_patterns.md](references/logic_bug_patterns.md) — Exhaustive logic bug patterns with detection methods, code examples, and root cause explanations
- [intermittent_bug_patterns.md](references/intermittent_bug_patterns.md) — Intermittent/sporadic bug patterns: race conditions, timing, state leaks, environment sensitivity
- [cross_module_analysis.md](references/cross_module_analysis.md) — Cross-module bug tracing: interface contracts, shared state auditing, protocol verification
- [debugging_guide.md](references/debugging_guide.md) — Strategic print placements for logic bugs, binary bisection strategy
- [report_template.md](references/report_template.md) — Two report formats: debugging-required and full analysis
