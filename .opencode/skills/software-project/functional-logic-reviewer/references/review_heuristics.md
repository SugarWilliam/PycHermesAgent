# Expert Review Heuristics

Thinking patterns and strategies used by world-class code reviewers. Load this when you need guidance on **how to think** during review, not just what to check.

## Table of Contents
1. [The Expert Reviewer Mindset](#1-the-expert-reviewer-mindset)
2. [Hypothesis-Driven Review Process](#2-hypothesis-driven-review-process)
3. [Reading Code Like a Debugger](#3-reading-code-like-a-debugger)
4. [Scenario-First Review](#4-scenario-first-review)
5. [Smell-to-Bug Deep Mapping](#5-smell-to-bug-deep-mapping)
6. [Cross-Module Reasoning](#6-cross-module-reasoning)
7. [Semantic Continuity And Last-Mile Checks](#7-semantic-continuity-and-last-mile-checks)
8. [Override And Policy Audits](#8-override-and-policy-audits)
9. [Concurrency Analysis Strategy](#9-concurrency-analysis-strategy)
10. [False Positive Reduction](#10-false-positive-reduction)
11. [Severity Calibration](#11-severity-calibration)
12. [Commit Message Forensics](#12-commit-message-forensics)

---

## 1. The Expert Reviewer Mindset

Expert reviewers differ from automated scanning in three key ways:

1. **They reason about intent**: "What was the developer trying to achieve?" before "Is this code correct?"
2. **They maintain a threat model**: For each change, they mentally simulate failure modes
3. **They follow the data**: They trace data from external input through processing to output, watching for corruption opportunities

**Core question chain for every change**:
1. What problem does this fix/feature solve?
2. What could go wrong in the normal path?
3. What could go wrong in every error path?
4. What happens when this code runs concurrently with other code?
5. What happens at the boundaries (first, last, empty, max, overflow)?
6. Who else depends on what this code changed?

---

## 2. Hypothesis-Driven Review Process

Instead of linearly scanning code, form and test hypotheses:

### Step 1: Generate Hypotheses (from change type)

```
Change type: "Fix timeout handling in keepalive"
Hypotheses:
  H1: Timer may fire after connection is freed (use-after-free)
  H2: Timeout value may be wrong unit (ms vs s)
  H3: Multiple timers may conflict (race condition)
  H4: Timer not cancelled on clean disconnect (resource leak)
```

### Step 2: Priority-Rank Hypotheses

Rank by: (probability × impact). Test highest-risk first.

### Step 3: Seek Evidence

For each hypothesis, actively search for confirming or disconfirming evidence in the code. Record:
- **Confirmed**: Found concrete execution path leading to the bug
- **Disproved**: Found guard/check that prevents the issue
- **Inconclusive**: Cannot determine from available code context

### Step 4: Generalize

If H1 confirmed → check **all other** timer callbacks for the same pattern.

---

## 3. Reading Code Like a Debugger

### The "Execute in Your Head" Technique

For critical code paths, mentally execute the code with specific inputs:

1. **Normal case**: Typical valid input → verify correct behavior
2. **Empty/zero case**: NULL, 0, empty string → verify no crash
3. **Boundary case**: MAX_INT, buffer-full, last-element → verify no overflow
4. **Error case**: Syscall fails, malloc returns NULL → verify cleanup
5. **Concurrent case**: Another thread modifies shared state mid-operation → verify safety

### The "What If This Line Fails?" Walk

For each function call in the critical path:
- What if it returns error?
- What if it blocks indefinitely?
- What if it was already called?
- What if the precondition doesn't hold?

### The "Invert the Fix" Test

For bug fixes, imagine the fix is applied in reverse:
- Does the original bug reappear?
- Does the fix address root cause or just symptom?
- Could the bug manifest differently elsewhere?

---

## 4. Scenario-First Review

When commit text or changelog contains a scenario matrix, policy statement, or override language, do not start from code diffs alone. Start from scenarios.

### The "Scenario Before Function" Rule

Normalize each text claim into:

1. Preconditions
2. Trigger
3. Expected result
4. Expected non-result

Examples of scenario-rich text:

- enabled vs disabled
- silent vs non-silent
- standby vs running
- armed vs disarmed
- privacy mode vs normal mode
- `bypass`, `ignore`, `break through`, `无视`, `突破`

If the text contains multiple rows of expected behavior, treat each row as a testcase. Do not mark the revision as correct until every row has a code-backed verdict.

### The "Half-Implementation" Warning

Many bugs are not total absences. They are partial implementations where:

- entry logic changed, but final sink logic did not
- one output path was updated, sibling paths were not
- semantic classification exists, but is not preserved to the decision point
- one filter layer was bypassed, but another later filter still blocks behavior

When code looks directionally correct, this is exactly when reviewers should slow down rather than speed up.

### The "Stop Only At Observable Behavior" Rule

Do not stop the review at:

- state assignment
- enum selection
- helper return value
- queued message construction
- intermediate callback registration

Stop only when you reach one of these:

- final output sink
- final veto/filter point
- external protocol boundary
- hardware-facing command
- persisted visible state

---

## 5. Smell-to-Bug Deep Mapping

### Memory Smells

| Smell | Probable Bug | Investigation |
|-------|-------------|---------------|
| `malloc` in a loop without size check | OOM / memory exhaustion | Check loop bounds, total allocation size |
| `realloc` without updating all pointers | Dangling pointer | Trace all references to original buffer |
| Cast from `void*` without size validation | Buffer overflow on mismatch | Compare sizeof at allocation vs usage site |
| `free()` then fall-through to default case | Use-after-free | Check all paths after free for data access |
| Missing `free` in one of N return paths | Leak | Map all return paths, verify cleanup on each |

### Concurrency Smells

| Smell | Probable Bug | Investigation |
|-------|-------------|---------------|
| Global variable without any lock | Data race | Check all access sites for protection |
| Lock acquired in callback/handler | Deadlock risk | Trace caller's lock state |
| `if (flag)` then `flag = 0` without lock | TOCTOU race | Check if flag is accessed concurrently |
| Thread creates resource, other thread frees | Lifetime management bug | Verify ordering guarantee exists |
| Mutex + condition variable without `while` loop | Spurious wakeup miss | Must be `while(!cond)` not `if(!cond)` |

### Logic Smells

| Smell | Probable Bug | Investigation |
|-------|-------------|---------------|
| Complex nested ternary | Logic inversion | Simplify mentally and re-evaluate |
| Duplicated condition in if/else chain | Dead code or wrong branch | Check if conditions are mutually exclusive |
| Switch without default | Unhandled enum value | Check if enum can be extended |
| Signed/unsigned comparison | Unexpected comparison result | Check ranges of both operands |
| `sizeof(array)` in function parameter | Always returns pointer size | Parameter decays to pointer |
| New event/type chosen upstream but never copied into outbound message | Semantic drop / wrong downstream behavior | Trace struct fields and message packing at every hop |
| Output category selected before queuing, but sink receives default value | Fallback to wrong policy or wrong filter bucket | Check zero-init structs, missing assignments, and default enum values |
| Commit says `bypass` or `ignore filters`, but only one guard changed | Half-bypass / residual veto point | Enumerate every later filter layer to see what still blocks |
| One user-visible feature name maps to multiple code paths | One path fixed, sibling path still broken | Split by owner and review each path separately |

### Embedded-Specific Smells

| Smell | Probable Bug | Investigation |
|-------|-------------|---------------|
| `memcpy` with hardware address | Missing cache flush/invalidate | Check DMA/MMIO context |
| `sleep`/`msleep` in atomic context | Kernel BUG | Trace context (ISR, spinlock held?) |
| Direct register write sequence | Missing barrier between writes | Check if order matters for HW |
| Interrupt enable without handler registered | Spurious interrupt crash | Verify handler installed first |
| Stack-allocated buffer > 1KB in kernel | Stack overflow risk | Kernel stack is typically 8KB |

---

## 6. Cross-Module Reasoning

### The Producer-Consumer Audit

For every data structure that crosses module boundaries:
1. **Schema**: Does producer's struct definition match consumer's?
2. **Lifecycle**: Who allocates? Who frees? Is ownership clearly transferred?
3. **Versioning**: If schema evolves, is backward compatibility maintained?
4. **Synchronization**: If shared, what's the locking protocol?

### The Interface Contract Check

For every function called across modules:
1. **Preconditions**: Does caller guarantee what callee assumes?
2. **Postconditions**: Does callee guarantee what caller expects?
3. **Error contract**: What errors can callee return? Does caller handle all of them?
4. **Thread-safety contract**: Is callee thread-safe? Does caller assume it is?

### The "Ripple Effect" Analysis

When a data type, struct field, or protocol changes:
1. `grep` for all usages across the entire codebase
2. For each usage, check if it needs update
3. Flag usages that were NOT updated but should have been

### The "Same Word, Different Owner" Audit

User-facing vocabulary is often overloaded. Terms like `alarm`, `chime`, `light`, `record`, `push`, `preview`, or `ring` may refer to multiple implementation owners.

For each overloaded term:

1. Enumerate all concrete owners
2. Map each owner to its entry point and final sink
3. Review them independently
4. Never transfer correctness from one owner path to another

---

## 7. Semantic Continuity And Last-Mile Checks

Some of the highest-value review findings come from discovering that a new semantic meaning was created but not preserved to where decisions are made.

### The "Semantic Carrier" Audit

Whenever a change introduces or repurposes:

- enum values
- bitmaps or flags
- struct fields
- message fields
- config fields
- policy tags

track the semantic carrier through the whole chain:

1. Where is it created?
2. Where should it be copied?
3. Where can it be defaulted, reset, overwritten, or dropped?
4. Which downstream branch depends on it?
5. What happens if the downstream branch sees the default value instead?

### Last-Mile Failure Patterns

Common last-mile failures:

- semantic field never serialized into outbound message
- outbound struct zero-initialized, but critical field never assigned
- field copied in one transport path but not another
- sink-side filter still keyed on old category
- sink-side policy uses default enum value, causing wrong routing or silent filtering

These are especially common in event-routing and policy-heavy code, because upstream behavior appears correct in logs while the final output still behaves like the old system.

---

## 8. Override And Policy Audits

When commit text says behavior should bypass, ignore, override, or break through existing rules, reviewers should assume there are multiple veto layers until proven otherwise.

### The "Enumerate All Filters" Rule

For an override requirement, explicitly list all relevant filter layers. Typical layers include:

- readiness checks
- standby / privacy / armed-state checks
- configuration enable switches
- silent / do-not-disturb windows
- online / connectivity checks
- rate limit / debounce / cooldown logic
- protocol-shaping or sink-side filtering

For each layer, answer one of three questions:

1. Is it intentionally bypassed?
2. Is it intentionally retained?
3. Was it never reviewed?

If the requirement says `ignore all filters` or equivalent, any surviving veto point is a bug.

### Policy Mismatch Heuristic

Policy bugs often look like valid code because every local branch makes sense in isolation. The defect appears only when the total policy is reconstructed end-to-end.

Good reviewer question:

`If I describe the full product rule in one sentence, which exact branches across modules collectively enforce that sentence?`

If that answer is incomplete, the policy is not fully implemented.

---

## 9. Concurrency Analysis Strategy

### Lock Graph Construction

For the changed code:
1. List all locks acquired (mutex, spinlock, rwlock, semaphore)
2. For each lock, trace the acquisition order in all callers
3. Draw directed graph: Lock_A → Lock_B means A acquired before B
4. **Cycle in graph = potential deadlock**

### Shared State Inventory

1. List all variables accessed in the changed function
2. For each variable, determine: local, thread-local, or shared?
3. For each shared variable, verify protection mechanism
4. For each protection mechanism, verify it's held at all access points

### The "Evil Thread" Thought Experiment

Imagine a malicious thread scheduler that always preempts at the worst possible moment:
- Right after a NULL check but before the dereference
- Right after a read but before the write-back
- Right after enqueueing but before setting the flag
- Would any of these cause a bug?

---

## 10. False Positive Reduction

### Before Reporting an Issue, Ask:

1. **Reachability**: Can this code path actually be reached in production?
   - Check if the function is called at all
   - Check if the problematic branch condition can actually be true
   
2. **Guard Elsewhere**: Is there a check earlier in the call chain that prevents the bad input?
   - Trace callers upward; there may be validation before reaching this point
   
3. **Intentional Design**: Could this be deliberate?
   - Some "leaks" are intentional (process-lifetime allocations)
   - Some "missing checks" are by design (caller guarantees validity)
   - If intentional, suggest adding a comment explaining why

4. **Environment**: Is the assumption correct for this embedded environment?
   - Single-threaded event loop → no races even without locks
   - Known hardware constraint → certain values impossible

5. **Did I stop too early?**
   - If the code only proves that an event was classified or queued, you do not yet know the final behavior
   - Re-check whether a downstream sink, filter, or transport layer can still change the outcome

### Confidence Assignment Rules

- **Confirmed**: You can construct a specific input sequence that triggers the bug
- **Likely**: The pattern is known-buggy AND no mitigating guard is found
- **Suspicious**: Pattern looks risky but you cannot prove reachability
- **FYI**: Technically imprecise but unlikely to impact in practice

---

## 11. Severity Calibration

### Blocker Indicators
- Affects data integrity (corruption, loss)
- Causes system halt (deadlock, panic, watchdog reset)
- Security vulnerability (buffer overflow with external input)
- No workaround exists

### High Indicators
- Feature doesn't work as intended
- Crash under specific but realistic conditions
- Performance degradation > 10x
- Backward compatibility break

### Medium Indicators
- Resource leak that manifests over long running time (days/weeks)
- Edge case not handled (but doesn't crash)
- Code path that "usually works" but isn't guaranteed

### Low Indicators
- Style inconsistency
- Missing log context (makes debugging harder)
- Minor inefficiency
- Duplicate code

---

## 12. Commit Message Forensics

### Systematic Audit Process

1. **Parse the commit message** into individual claims:
   - "Fix X" → expect to see code that prevents X
   - "Add feature Y" → expect to see new code implementing Y
   - "Optimize Z" → expect to see performance improvement in Z
   - Scenario matrices → expect one code-backed verdict per row
   - Override language → expect review of all filter layers, not just the edited one

2. **Forward check** (message → code): For each claim, find the corresponding code change. No code found = **unimplemented claim**.

3. **Reverse check** (code → message): For each significant code change, find the corresponding description. No description = **undocumented change**.

4. **Semantic check**: Does the code *actually* fix/implement what the message claims? A common pattern: message says "fix null pointer crash" but code only adds a log without fixing the root cause.

5. **Scenario closure check**: If the message describes a user-visible condition pair such as `silent/non-silent`, `enabled/disabled`, `standby/running`, or `all other outputs must not react`, verify both sides explicitly. Missing one side is not a partial pass; it is an incomplete implementation.

### Red Flags in Commit Messages
- Vague: "fix bug", "update code", "misc changes"
- Scope mismatch: "fix audio issue" but changes touch network module too
- Multiple unrelated fixes in one commit
- Message mentions workaround but doesn't explain why proper fix wasn't done
- Matrix-style requirements with no matching end-to-end verification in review notes
