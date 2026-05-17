---
name: linux-bug-analyzer
description: >
  Systematic bug analysis and root-cause localization for Linux userspace
  C/C++ applications (embedded Linux, daemon, service, CLI tool). Combines
  hypothesis-driven reasoning, full call-chain tracing, log analysis, and
  C/C++-specific defect pattern matching to pinpoint root causes. Use this
  skill when: (1) user describes a bug with symptoms and expected behavior in
  a Linux C/C++ application; (2) user provides log output, printf/syslog
  traces, or GDB backtrace to help locate a bug; (3) user asks to analyze,
  diagnose, debug, or locate the root cause of unexpected behavior; (4) user
  mentions keywords like "bug", "defect", "crash", "segfault", "coredump",
  "异常", "BUG分析", "定位问题", "崩溃", "不符合预期", "日志分析",
  "core dump", "死锁", "内存泄漏"; (5) user provides C/C++ code snippets
  together with runtime behavior that deviates from expectation.
---

# Bug Analyzer

Systematic bug analysis for Linux userspace C/C++ applications. Hypothesis-driven reasoning → full context expansion → call-chain tracing → root cause determination.

## Input Requirements

Collect from user before analysis:

| Input | Required | Description |
|-------|----------|-------------|
| **Bug Description** | Yes | Observed symptom, error message, or abnormal behavior |
| **Expected Result** | Yes | Correct behavior the user expects |
| **Log / Print Output** | Optional | Runtime logs, debug prints, trace output |
| **Relevant Code** | Optional | C/C++ source files or snippets suspected to contain the bug |
| **Reproduction Steps** | Optional | How to trigger the bug |
| **Environment** | Optional | Linux distro/kernel, CPU arch, toolchain, build config |
| **GDB Backtrace** | Optional | `bt full` output from core dump or live attach |

If user omits required inputs, ask before proceeding.

---

## The Iron Law

```
NO FIX PROPOSALS BEFORE COMPLETING AT LEAST THROUGH PHASE 4.
SEEING SYMPTOMS ≠ UNDERSTANDING ROOT CAUSE.
```

---

## Analysis Workflow

### Phase 0: Discipline Gate

Before deep analysis, enforce rapid checks to avoid wasted effort:

#### 0a. Reproducibility Gate

- Can the bug be triggered reliably? What are the exact steps?
- If **not reproducible** → do NOT guess. Ask user for more info, or suggest targeted instrumentation (see [debugging_tools.md](references/debugging_tools.md)) to capture the next occurrence.
- Only proceed after establishing reproduction steps or sufficient log/coredump evidence.

#### 0b. Recent Changes Check

- **Mandatory**: Check what changed recently before forming any hypothesis:
  - SVN/Git diff of last N commits touching related modules
  - New dependencies, config changes, build flag changes, toolchain upgrades
  - Environmental differences (board revision, kernel version, library version)
- If a recent change is found in the bug's code path → Hypothesis #1 priority
- If regression ("it used to work") → the diff is the #1 evidence source

#### 0c. Working Reference Search

- Search codebase for **functionally similar code that works correctly**:
  - Same module's handling of a different but similar command/event
  - Same feature on a different platform/board
  - Previous working version from VCS history
- Keep the reference for comparison in Phase 3

#### 0d. Multi-Component Boundary Check

When multiple processes/components are involved (App → IPC → driver → MCU):

- Log data entering and exiting each component boundary
- Run once to identify **WHERE** data breaks
- Then focus analysis on the failing component

### Phase 1: Symptom Characterization

1. **Classify** the bug type:

   | Category | Indicators |
   |----------|------------|
   | Crash | segfault, bus error, abort, core dump, stack smashing |
   | Hang / Deadlock | no response, timeout, watchdog reset, 100% CPU, pthread stuck |
   | Data Corruption | wrong output, garbled data, CRC mismatch |
   | Logic Error | wrong behavior, incorrect state, wrong branch taken |
   | Resource Leak | OOM, fd exhaustion (`EMFILE`), gradual memory growth |
   | Race Condition | intermittent, timing-dependent, works under GDB |
   | IPC / Protocol Error | message garbled, partial recv, struct size mismatch |
   | Boot / Init Order | fails on cold boot, works after restart |

2. **Extract key facts**: trigger condition, first occurrence timing, scope of impact.

### Phase 2: Log Trace Analysis

When user provides log output:

1. **Timeline Reconstruction**
   - Extract timestamps → chronological event sequence
   - Identify **last normal event** and **first abnormal event**
   - Bug triggers between these two points

2. **Key Pattern Extraction**

   | Log Pattern | Likely Root Cause |
   |-------------|-------------------|
   | `segfault at 0x0` | NULL pointer dereference |
   | `segfault at 0xNN` (small addr) | Struct member access via NULL base (offset = member offset) |
   | `SIGABRT` / `Aborted` | `assert()` failed, double-free detected by glibc |
   | `malloc failed` / `ENOMEM` | Memory leak, fragmentation, or ulimit |
   | `stack smashing detected` | Buffer overflow on stack |
   | `double free or corruption` | Heap corruption |
   | `pthread_mutex_lock` hangs | Deadlock |
   | Value deviates from expected | Logic error near last correct print |
   | Function entry logged but exit missing | Crash or hang inside that function |
   | Repeating pattern | Infinite loop or retry storm |

3. **GDB Backtrace Analysis** (when available)
   - Parse `bt full` → crash call stack with local variable values
   - Start analysis from deepest frame, trace upward for root cause

4. **Print Trace Narrowing**
   - Identify which prints executed and which did not → narrow to code region between last-seen and first-missing print
   - Build **variable value timeline** to spot where values diverge

### Phase 3: Hypothesis Formation

#### 3a. Working Reference Comparison (from Phase 0c)

If working reference found, compare broken code vs reference line by line. Each difference that correlates with the symptom becomes a high-priority hypothesis input.

#### 3b. Generate 3-5 Ranked Hypotheses

Based on symptom + logs + recent changes + reference comparison:

1. Form **3-5 hypotheses** from most to least likely
2. For each: suspected root cause → code location → verification method
3. Prioritize by:
   - **Recent change regression** (Phase 0b): check FIRST
   - Consistency with ALL observed symptoms
   - Known bug patterns (see [common_bug_patterns.md](references/common_bug_patterns.md))

### Phase 4: Full Context Expansion and Call-Chain Tracing

For each hypothesis, expand complete context and trace full call chain:

#### 4a. Full Context Expansion (Mandatory)

Never analyze a function in isolation:

1. Read the **entire suspected function**
2. Read **surrounding context**: interacting functions, headers, macros, global/static variables
3. Read **related data structures**: struct definitions, initialization code, lifecycle management

#### 4b. Call-Chain Tracing (Mandatory for Logic Problems)

**Upward** (callers → suspected function):
- Identify all callers, what arguments are passed, under what conditions
- Continue until reaching entry point: `main()`, message handler, timer callback, signal handler, RPC handler

**Downward** (suspected function → callees):
- What does each callee actually do? Read implementations, not just prototypes
- Are preconditions met? Error returns checked? Side effects expected?
- Continue until reaching sink: syscall, IPC send, hardware register, global state assignment

**Lateral** (cross-module data flow):
- Find shared state (globals, shared memory, message queues)
- Find all other writers/readers — check synchronization and data format consistency

**Verification checklist**:

- Entry point args validated?
- Each layer transforms data correctly for the next?
- Callee preconditions guaranteed by calling context?
- Error returns checked by all callers?
- Shared state protocol consistent across all accessors?
- Function safe in its actual invocation context (signal handler, timer, thread)?
- Module initialized before use? Could be called after deinit?

#### 4c. Logic Verification

Simulate execution step by step through the call chain using the reproduction scenario. At each step compare against expected behavior. **Pinpoint the divergence**: the exact line where actual behavior first deviates from expected = root cause location.

#### 4d. Known Defect Pattern Check

Cross-check against [common_bug_patterns.md](references/common_bug_patterns.md). Key categories:

- §1: Memory errors (use-after-free, buffer overflow, double free, sizeof errors)
- §2: Concurrency (data race, deadlock, missing unlock, spurious wakeup)
- §3: Logic errors (condition reversal, wrong operator, integer overflow)
- §4: Resource leaks (fd, memory, thread, timer)
- §5-6: State machine defects, IPC/protocol errors
- §10: C language traps (strict aliasing, signed/unsigned, integer promotion)
- §11-12: Embedded Linux system patterns, network socket patterns

#### 4e. Cross-Reference with Log Evidence

- Map each log entry to a point in the traced call chain
- Does the hypothesis explain ALL symptoms and log timing?
- If not → refine or discard

### Phase 5: Root Cause Determination and Fix

1. **Confirm root cause**: exact location, defective code, why it fails, how it explains each symptom

2. **Propose fix**: minimal corrective change, rationale, side effects, defensive measures

3. **Suggest verification**: specific test case, edge cases, regression scenarios

4. **Fix failure escalation**:
   - Attempt 1-2 failed → return to Phase 3, re-form hypotheses (failure itself is evidence)
   - Attempt ≥3 failed → **STOP. Question the architecture.** Signs of wrong architecture:
     - Each fix reveals new coupling in a different place
     - Fix requires "massive refactoring"
     - Each fix creates new symptoms elsewhere
   - **Pause and discuss with user** before further attempts

---

## Report Format

Use the template in [report_template.md](references/report_template.md) for structured output.

---

## Red Flags — STOP and Return to Phase 0

| Red Flag Thought | What's Wrong |
|-----------------|-------------|
| "I see the crash location, let me fix it" | Crash site is symptom, not root cause. Trace the call chain. |
| "It's probably NULL, let me add a check" | NULL guard hides the bug. Find WHY it's NULL. |
| "Let me fix multiple things at once" | Can't isolate what worked. One change at a time. |
| "The log says X, so obviously Y" | One log line is not enough. Build the full timeline. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Escalate. |
| "Not reproducible, but I think I know" | No reproduction = no evidence. Enforce Phase 0a. |
| "The GDB backtrace shows the answer" | Backtrace shows WHERE, not WHY. Trace upward. |
| Proposing fixes before Phase 4 complete | The Iron Law: no fixes before call-chain tracing. |

These apply at **every phase transition**. Before moving Phase N → N+1, verify no shortcuts.

---

## References

- [common_bug_patterns.md](references/common_bug_patterns.md) — Categorized C/C++ bug patterns with detection methods, code examples, and root causes. §1-9: Memory, concurrency, logic, resource, state machine, IPC, string, Linux system, C++ patterns. §10: C language traps. §11: Embedded Linux system patterns. §12: Network socket patterns.
- [debugging_tools.md](references/debugging_tools.md) — Print macros (DBG/DBG_ERR/DBG_PTR), strategic print placement, binary bisection strategy, GDB quick commands.
- [report_template.md](references/report_template.md) — Structured report template for analysis output.
