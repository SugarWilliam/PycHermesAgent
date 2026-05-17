---
name: functional-logic-reviewer
description: >
  Expert-level functional logic verification for embedded Linux code changes.
  Combines hypothesis-driven review, mandatory call-chain tracing, 7-dimension
  verification, and embedded-systems domain expertise to maximize bug detection.
  Use this skill when: (1) reviewing SVN/Git diffs for embedded Linux projects
  (IPC, network, audio, video, storage, system modules); (2) performing deep
  functional verification beyond structural review; (3) auditing changes involving
  state machines, concurrency, IPC, timers, DMA, ISR, or power management;
  (4) conducting version-release architecture audits; (5) user mentions keywords
  like "code review", "functional review", "logic verification", "call-chain
  analysis", "impact analysis", or "审查"/"评审"/"逻辑验证";
  (6) user provides a requirement document (from code-review-req skill or manually
  written) and requests requirement-driven deep review.
---

# Functional Logic Reviewer

Expert-level functional logic verification for embedded Linux code changes. Maximizes defect discovery through hypothesis-driven analysis, mandatory call-chain tracing, and embedded-systems domain expertise.

## SVN Log and Diff Retrieval

```bash
# Markdown log + per-revision diff files
python scripts/svn_log_diff.py --repo <repo> --path <path> --rev-start <r1> --rev-end <r2-or-HEAD> --log-output <file.md> --diff-outdir <dir>
```

Use `HEAD` for latest revision.

Output contract:
- One Markdown file containing revision index, structured metadata, commit message, and changed paths
- One diff file per revision in the diff output directory

---

## Review Modes

This skill supports two review modes. Select based on available input:

| Mode | Trigger | Approach |
|------|---------|----------|
| **Diff-Driven** (default) | User provides diffs/changelogs only | Hypothesis-driven: infer intent from code → form bug hypotheses → verify |
| **Requirement-Driven** | User provides a requirement document (with or without diffs) | Scenario-driven: verify each requirement against code → trace call chains per scenario |

### Requirement-Driven Review Mode

When the user provides a requirement document (typically produced by the `code-review-req` skill and calibrated by a human), switch to requirement-driven mode:

1. **Parse Requirements**: Extract each requirement with its user scenarios, state transitions, and implicit constraints
2. **Map Requirements → Code**: For each requirement, identify the code regions (files, functions, data structures) that implement it
3. **Scenario Trace**: For each user scenario in the requirement:
   - Trace the **complete execution path** from user action to system response
   - At each step, verify the code does what the requirement says it should
   - Identify **gaps**: scenarios that have no corresponding code path
   - Identify **excess**: code paths that have no corresponding requirement (potential unintended behavior)
4. **State Transition Verification**: For requirements involving state/mode transitions:
   - Build the **complete state transition table** from requirements
   - Compare against actual code implementation
   - Report missing transitions, invalid transitions, and transitions without proper cleanup
5. **Implicit Constraint Check**: For each human-annotated implicit constraint:
   - Search code for the enforcement point
   - If not enforced in code, report as **Confirmed** issue
6. **Cross-Requirement Consistency**: For requirements marked as related:
   - Verify they do not conflict in implementation
   - Verify shared resources are properly coordinated
7. **Apply Phase 2–5** (7-dimension verification, embedded checks, issue classification) to every finding

**Output**: Same report format as Phase 6, but organized **per requirement** instead of per revision. Each requirement section includes:
- Requirement text (from calibrated document)
- Mapped code locations
- Per-scenario verdict (Pass / Fail with evidence)
- Issues found with severity + confidence

**Key advantage over diff-driven mode**: Requirement-driven mode catches **omission bugs** — features the user expects but the code never implements. Diff-driven mode can only find bugs in code that exists; requirement-driven mode also finds bugs in code that is **missing**.

---

## Diff-Driven Review Workflow

Default workflow when no requirement document is provided.

### Phase 0: Triage & Prioritize

Before deep analysis, **quick-scan all changes and rank by risk**:

| Risk Signal | Priority |
|-------------|----------|
| Concurrency / lock / ISR / timer changes | 🔴 Critical |
| State machine / lifecycle changes | 🔴 Critical |
| IPC / protocol / struct layout changes | 🔴 Critical |
| Memory alloc/free / DMA / mmap changes | 🟡 High |
| Error handling / exception path changes | 🟡 High |
| Config / parameter / boundary changes | 🟡 High |
| Simple value fix / log / comment changes | 🟢 Low |

Allocate review depth proportional to risk. Skip deep call-chain for 🟢 Low items.

### Phase 1: Hypothesis Formation

**Before reading code details, form bug hypotheses from the change type:**

| Change Type | Likely Bug Hypotheses |
|-------------|----------------------|
| Mutex/lock modification | Deadlock, priority inversion, lock ordering violation, missing unlock on error path |
| Timer create/delete | Timer leak, callback on deleted timer, use-after-free in callback context |
| Buffer/memory operation | Buffer overflow, off-by-one, DMA alignment fault, cache coherency miss |
| State transition change | Missing transition, unreachable state, transition without cleanup |
| IPC/RPC message change | Struct size mismatch, field offset drift, backward compatibility break |
| Network socket operation | FD leak, SIGPIPE, partial send/recv, non-blocking EAGAIN miss |
| ISR/interrupt handler | Non-async-signal-safe call, excessive ISR duration, shared state without volatile/barrier |
| Power management | Wake source not registered, suspend with held lock, device state not restored |
| File/flash operation | TOCTOU race, fsync missing, wear-leveling ignorance, partial write, **fopen/open without paired fclose/close on success path** (goto-cleanup bypassed by early `return`), fd exhaustion (EMFILE) after sustained triggering |
| fork/exec/daemon code | Zombie leak, fd inheritance, signal mask inheritance, PID file race |
| pthread creation/sync | Cancellation leak, stack overflow, spurious wakeup, priority inversion |
| Serial/UART config | termios mode error, partial read, flow control mismatch, baud rate wrong |
| Signal handler change | Non-async-signal-safe call, EINTR not retried, mask not restored |
| RT scheduling change | SCHED_FIFO starvation, malloc in RT path, mlockall missing, page fault |
| Macro definition/invocation | Multi-eval side effects, missing parentheses, do-while(0) missing, stringification indirection |
| Type cast / pointer aliasing | Strict aliasing violation, alignment fault, signed/unsigned confusion, integer truncation |
| Bit operation | Shift amount >= width (UB), signed left-shift overflow, signed bitwise ops, non-portable bitfields |
| Integer arithmetic | Signed overflow UB (compiler removes checks), implicit promotion of narrow types, mixed signed/unsigned comparison |

**Then verify or disprove each hypothesis** against the actual code.

### Phase 2: Deep Analysis (Per Change)

1. **Extract**: files, functions, parameters, return values changed
2. **Context**: Read the **entire containing function** (not just ±15 lines). If the function is a callback or handler, also read the registration/dispatch site.
3. **Call-Chain Tracing (Required for 🔴🟡)**:
   - **Upward**: Trace callers → entry points (RPC/MSG/timer/CLI/ISR/signal)
   - **Downward**: Trace callees → sinks (IO/IPC/config/storage/hardware registers)
   - **Lateral**: Identify cross-module data flow (shared structs, global state, message queues)
4. **7-Dimension Verification**:

   | Dimension | Focus |
   |-----------|-------|
   | Functionality | Code matches changelog (and requirement doc if provided)? Commit msg matches actual change? |
   | State Machine | All transitions defined? Init/final states correct? |
   | Boundary | NULL, 0, MAX, negative, overflow, alignment |
   | Timing | Race, deadlock, ordering, ISR safety, re-entrancy |
   | Config | Consistent across modules? Defaults correct? |
   | Exception | All error **and success** paths handled? Resources cleaned up at **every `return` site**? In `goto cleanup` pattern: does any early `return` bypass the label? |
   | Impact | API/ABI compat? Cross-module contract intact? |

5. **Commit Message Audit**: For each revision, systematically verify:
   - Every feature described in the message → find corresponding code implementation
   - Every code change → find corresponding description in the message
   - Report **undocumented changes** and **unimplemented claims** explicitly

### Phase 3: Embedded Linux Deep Checks

Apply domain-specific checks. See [embedded_linux_pitfalls.md](references/embedded_linux_pitfalls.md) for OS/hardware interaction patterns and [c_language_pitfalls.md](references/c_language_pitfalls.md) for C language standard-level UB and traps.

**Kernel/Driver Layer:**
- **Memory**: DMA alignment (cache-line), mmap page boundaries, slab/kmalloc size classes, IOMMU mapping
- **Concurrency**: spinlock in atomic context, mutex in ISR (forbidden), RCU read-side critical section crossing schedule point, lock ordering across modules
- **IPC**: struct packing/padding consistency across processes, endianness in network protocols, message queue overflow handling
- **Timing**: timer callback context (softirq vs workqueue), jiffies wrap-around, CLOCK_MONOTONIC vs CLOCK_REALTIME
- **Resources**: fd/resource leak on **any** exit path (error, success, or exception); enumerate every `return`/`throw`/`goto` exit point and verify each one releases all acquired resources before leaving the function; RAII + manual resource mix is especially risky — RAII destructors run automatically on all exits but manually managed handles (`FILE*`, fd, mutex) are only freed where explicitly coded; success-path early returns are the most overlooked leak source
- **Init/Shutdown**: module_init/module_exit symmetry, probe/remove resource pairing, power-off sequence ordering

**Application Layer (Userspace):**
- **Process**: zombie leak (missing waitpid), daemon pattern correctness, PID file race, fd inheritance on exec
- **pthread**: cancellation cleanup, stack size for embedded, spurious wakeup (while vs if), mutex attribute (recursive/inherit)
- **Memory**: heap fragmentation in long-running process, mmap leak, stack overflow via VLA/recursion, use-after-free via stale cache
- **Signals**: non-async-signal-safe calls in handler, EINTR retry, signal mask inheritance on fork/exec
- **Serial/UART**: termios raw mode, partial read framing, hardware flow control, non-standard baud rate
- **Watchdog**: feed during long operations, magic close character, timeout vs worst-case latency
- **RT Scheduling**: SCHED_FIFO starvation, mlockall for deterministic latency, priority inversion, no malloc in RT path
- **Toolchain**: host vs target binary, library ABI mismatch, float ABI mismatch (ARM), sizeof(long) portability
- **Syscall**: errno overwrite, CLOCK_MONOTONIC vs REALTIME, command injection via system()/popen(), locale-dependent parsing

### Phase 3c: Resource Release Completeness Check

**Mandatory for any function that acquires non-RAII resources (🟡 High risk):**

1. **Inventory all non-RAII resources acquired**: `fopen`, `open`, `malloc`, `pthread_mutex_lock`, `socket`, custom handle alloc, etc.
2. **List every exit point**: every `return`, `throw`, `goto`, and macro-generated exit — distinguish macros that expand to `goto` (reach the centralized release site) vs. macros that expand to `return` directly (skip it).
3. **For each exit point**: verify it releases all resources acquired above it before leaving the function scope.
4. **Cross-check RAII scope**: if RAII (C++ destructor / smart pointer) manages *some* resources but `FILE*`/fd is managed manually, the RAII destructor runs on *all* exits — but the manual resource is only freed where explicitly coded. Any exit that bypasses the release site leaks the manual resource even though RAII resources are safe.
5. **Success path is the most dangerous**: reviewers instinctively check error paths; success-path early `return OK` is frequently overlooked as a leak source.

**Quick check pattern** (mentally scan the function):
```
For each resource R acquired with fopen/open/malloc/lock:
  Is R released on every exit path?
  Does any early return/throw/goto skip releasing R?  ← This is the bug
```

See [embedded_linux_pitfalls.md § 22](references/embedded_linux_pitfalls.md) for patterns and fix examples.

### Phase 3b: Naming Convention & Spelling Check

Apply to all new/renamed identifiers (functions, variables, types, macros, files). See [naming_conventions.md](references/naming_conventions.md) for full rules.

**Linux Kernel Style (mandatory)**:
- Functions/variables: `snake_case` lowercase — e.g., `get_frame_count`, `buf_size`
- Types (typedef): `snake_case_t` only for opaque types; prefer bare `struct` name otherwise
- Macros/constants: `UPPER_SNAKE_CASE` — e.g., `MAX_RETRY_COUNT`, `BUF_ALIGN`
- Struct/enum tags: `snake_case` — e.g., `struct msg_header`, `enum stream_state`
- Bool variables/fields: prefix with `is_`/`has_`/`can_`/`should_` — e.g., `is_running`, `has_audio`
- Callbacks: suffix `_cb` or `_handler` — e.g., `timer_expire_cb`, `msg_recv_handler`
- No CamelCase, no Hungarian notation (`dwSize`, `lpBuffer`), no type prefix (`int_count`, `str_name`)

**Spelling & Abbreviation Rules**:
- All words in identifiers must be **correctly spelled** English words — flag typos (e.g., `recieve` → `receive`, `sucess` → `success`, `lenght` → `length`)
- Abbreviations must follow **industry-standard conventions**. Acceptable:

  | Abbreviation | Full Word | | Abbreviation | Full Word |
  |---|---|---|---|---|
  | `buf` | buffer | | `msg` | message |
  | `ctx` | context | | `cfg` | config |
  | `cmd` | command | | `cb` | callback |
  | `cnt` | count | | `len` | length |
  | `dev` | device | | `fd` | file descriptor |
  | `err` | error | | `fmt` | format |
  | `idx` | index | | `init` | initialize |
  | `itr`/`iter` | iterator | | `max`/`min` | maximum/minimum |
  | `num`/`nr` | number | | `pkt` | packet |
  | `ptr` | pointer | | `prev`/`next` | previous/next |
  | `req`/`resp` | request/response | | `ret` | return value |
  | `rx`/`tx` | receive/transmit | | `src`/`dst` | source/destination |
  | `str` | string | | `tmp`/`temp` | temporary |
  | `val` | value | | `info` | information |
  | `alloc` | allocate | | `dealloc` | deallocate |
  | `param` | parameter | | `stat`/`stats` | statistics |
  | `sync`/`async` | synchronous/asynchronous | | `addr` | address |
  | `desc` | descriptor | | `mgr` | manager |

- Non-standard abbreviations must appear in project-level glossary or adjacent comment. Flag unlisted abbreviations as naming issues (Low severity).

### Phase 4: Cross-Revision Correlation

When reviewing multiple revisions:
- Detect **conflicting changes** across revisions (one adds what another removes)
- Detect **incomplete fix chains** (fix A addresses symptom but root cause is in different area)
- Detect **scattered changes** that should be atomic (struct definition changed in rev N, but users not updated until rev N+3)
- Detect **regression introductions** (rev N+1 undoes the fix from rev N)

### Phase 5: Issue Classification

**Confidence Levels** (reduces false positives):

| Confidence | Meaning | Action |
|------------|---------|--------|
| **Confirmed** | Proven bug with concrete execution path | Must fix |
| **Likely** | Strong evidence, hard to disprove | Should fix |
| **Suspicious** | Pattern matches known bug class, needs verification | Investigate |
| **FYI** | Style, maintainability, minor risk | Optional |

**Severity Levels**:

| Severity | Definition | Example |
|----------|------------|---------|
| **Blocker** | System crash, data corruption, undefined behavior, deadlock | Kernel panic, flash corruption |
| **High** | Functional failure, transaction incomplete, security hole | Stream stops, auth bypass |
| **Medium** | Boundary miss, resource leak risk, degraded reliability | Slow leak over days |
| **Low** | Style, logging, minor maintainability | Missing log context |

**False Positive Reduction** — before reporting, verify:
1. Is the suspicious code path actually reachable?
2. Is there a guard/check elsewhere that prevents the issue?
3. Could this be intentional design? (If so, document why)

### Phase 6: Report Generation

Generate `review_report.md` at repo root. Record total review time.

Per changelog entry include:
1. **Revision, Author, Date, Commit Message**
2. **Files & Functions Modified** (with line ranges)
3. **Call-Chain Summary**: entry → function → sinks (with cross-module edges)
4. **7-Dimension Verdict**: Pass/Fail per dimension with evidence
5. **Commit Message Audit**: Match/Mismatch with specifics
6. **Issues Found**: Severity + Confidence + Code location + Root cause + Fix suggestion
7. **Regression Test Recommendations**

Final section: **Overall Assessment** with aggregate risk score.

---

## Code Smell → Bug Mapping (Quick Reference)

| Smell | Predicted Bug |
|-------|---------------|
| `malloc` without paired `free` in error path | Resource leak |
| Non-RAII resource acquired, but one or more exit points (`return`/`throw`/macro) skip the release site | Resource leak on that exit path (incl. success path) |
| `fopen`/`open` acquired, and an early success-path exit bypasses the `fclose`/`close` | FD leak on every successful call → eventual EMFILE |
| C++ RAII manages some resources, `fclose`/`free` manages others in same function | Partial leak: RAII destructor runs on all exits but manually managed resources skipped at exits that bypass the explicit release site |
| `memcpy` with `sizeof(pointer)` instead of `sizeof(struct)` | Buffer underflow / data corruption |
| Cast suppressing compiler warning | Type confusion / truncation |
| Nested locks without consistent ordering | Deadlock |
| `sprintf` instead of `snprintf` | Buffer overflow |
| Timer callback accessing freed structure | Use-after-free |
| `errno` checked after multiple syscalls | Wrong errno attribution |
| Boolean parameter controlling behavior | Logic inversion risk |
| `unsigned - unsigned` without underflow guard | Integer wrap-around |
| `time()` for interval measurement | Wall-clock jump vulnerability |
| `printf` format vs argument type mismatch | Stack corruption / UB |
| Recursive function without depth limit | Stack overflow |
| Global variable modified in ISR without `volatile` | Compiler optimization hides update |
| `strncpy` without explicit null terminator | Unterminated string |
| `fork()` without `waitpid` or SIGCHLD handler | Zombie process leak |
| `system()`/`popen()` with external input | Command injection |
| `if (!cond)` instead of `while (!cond)` before `cond_wait` | Spurious wakeup miss |
| `malloc` in RT (`SCHED_FIFO`) thread | Non-deterministic latency / page fault |
| Missing `O_CLOEXEC` on `open()`/`socket()` | FD leak to child process |
| `select()` with fd >= 1024 | Buffer overflow (FD_SETSIZE) |
| Serial port without `cfmakeraw()` for binary protocol | Data corruption (0x0A eaten by terminal layer) |
| `strtod()`/`sscanf("%f")` without locale check | Decimal point misparse in non-C locale |

---

## References

- [embedded_linux_pitfalls.md](references/embedded_linux_pitfalls.md) — Embedded Linux domain-specific bug patterns and hardware-software interaction pitfalls
- [c_language_pitfalls.md](references/c_language_pitfalls.md) — C language standard-level undefined behavior, implicit conversions, macro traps, and common logic pitfalls
- [naming_conventions.md](references/naming_conventions.md) — Linux-style naming rules, standard abbreviation table, and common misspelling list
- [review_heuristics.md](references/review_heuristics.md) — Expert reviewer thinking patterns, smell-to-bug deep mappings, and review strategy guidance
- [verification_template.md](references/verification_template.md) — Detailed verification checklist for manual test planning
- [issue_patterns.md](references/issue_patterns.md) — Common issue patterns with detection methods and code examples
