# Intermittent Bug Patterns

Patterns specific to intermittent/sporadic bugs that don't always reproduce. These are the hardest bugs to find — they are deterministic bugs with hidden preconditions.

## Table of Contents

1. [Race Conditions](#1-race-conditions)
2. [Timing Dependencies](#2-timing-dependencies)
3. [State Leak & Residual State](#3-state-leak--residual-state)
4. [Uninitialized Data](#4-uninitialized-data)
5. [Resource Sensitivity](#5-resource-sensitivity)
6. [Environment & Configuration](#6-environment--configuration)
7. [Analysis Strategy for Intermittent Bugs](#7-analysis-strategy-for-intermittent-bugs)

---

## 1. Race Conditions

### 1.1 Classic Data Race

Two threads access shared data, at least one writes, no synchronization.

**Hidden precondition**: Thread scheduling must interleave in a specific way.

```c
// Thread A:                    // Thread B:
shared_state = PROCESSING;      if (shared_state == IDLE)
do_work();                          start_new_request();  // BUG: may see IDLE
shared_state = IDLE;             //  before A finishes PROCESSING
```

**Why intermittent**: Depends on OS scheduler decisions — CPU load, interrupt timing, core migration.

**Detection**: List all shared variables. For each, verify ALL access sites are protected by the same lock. Run with ThreadSanitizer.

### 1.2 TOCTOU (Time-Of-Check-To-Time-Of-Use)

```c
if (file_exists(path)) {        // CHECK
    // Another process deletes file here
    fd = open(path, O_RDONLY);  // USE — may fail
}

if (queue_count > 0) {          // CHECK
    // Another thread drains queue here  
    item = dequeue();            // USE — may return NULL
}
```

**Detection**: Find check-then-act patterns on shared resources. Verify atomicity.

### 1.3 Lock Ordering Deadlock

```c
// Thread A: lock(X) → lock(Y)
// Thread B: lock(Y) → lock(X)
// Deadlock only when A holds X and B holds Y simultaneously
```

**Why intermittent**: Requires both threads to be in the critical section at the same time.

**Detection**: Build lock acquisition order graph for all threads. Cycle = potential deadlock.

### 1.4 ABA Problem

```c
// Thread A reads value = "A", gets preempted
// Thread B changes value A → B → A
// Thread A resumes, sees "A", assumes nothing changed
// BUG: internal state associated with "A" is now different
```

**Detection**: Check compare-and-swap patterns, or any check-then-act on values that can cycle back.

### 1.5 Signal Handler Race

```c
void handler(int sig) {
    processing_flag = 1;  // Set in signal handler
}

void main_loop() {
    if (!processing_flag) {
        // Signal arrives HERE — between check and blocking call
        blocking_read();  // BUG: misses the signal, blocks forever
    }
}
```

**Detection**: Check for non-atomic check-then-block patterns around signal handling. Use `pselect`/`ppoll`/`signalfd` instead.

---

## 2. Timing Dependencies

### 2.1 Initialization Order Race

```c
// Thread A: starts module X
// Thread B: starts module Y, immediately calls module X API
// BUG: if B starts before A is fully initialized, X API crashes
```

**Detection**: Check if there's a synchronization mechanism (event, barrier, ready-flag) between dependent init sequences. Check `pthread_create` order and whether new thread waits for deps.

### 2.2 Timer / Timeout Window

```c
// Start operation, set 5s timeout
start_operation();
timer_set(5000, timeout_handler);

// If operation completes in exactly 5000ms, it's a race:
// Does completion handler run first, or timeout handler?
// BUG: both may run, or timeout cancels a completed operation
```

**Detection**: Check timer cancel logic — is timer reliably cancelled when operation completes? Is the callback safe if operation already completed?

### 2.3 Message Ordering

```c
// Module A sends MSG_CONFIG then MSG_START
send(MSG_CONFIG);
send(MSG_START);

// Module B receives via two different channels or threads
// BUG: MSG_START may arrive before MSG_CONFIG under load
```

**Detection**: Check if message ordering is guaranteed by the transport. If not, verify receiver handles out-of-order delivery.

### 2.4 Retry Storm

```c
// On failure, retry immediately
while (send(msg) < 0)
    ;  // BUG: if peer is temporarily busy, this burns CPU and
       //       may worsen the condition, creating intermittent timeouts elsewhere
```

**Detection**: Check retry loops for backoff/delay/limit. Unbounded retries create cascading timing failures.

---

## 3. State Leak & Residual State

### 3.1 Static Variable Not Reset

```c
int process_request() {
    static int error_count = 0;
    // BUG: error_count accumulates across requests
    // After enough errors from DIFFERENT requests, threshold triggers
    if (++error_count > MAX_ERRORS)
        return FATAL;
}
```

**Why intermittent**: Depends on history of previous operations.

### 3.2 Stale Cache / Lookup Table

```c
// Cache entry created during first access
cache[key] = compute_value(key);

// Later, underlying data changes but cache not invalidated
result = cache[key];  // BUG: returns stale value
```

**Why intermittent**: Depends on whether data changed since caching and whether the cached entry is hit.

### 3.3 Incomplete Cleanup on Error

```c
int start_session() {
    alloc_buffers();
    if (connect() < 0) {
        // BUG: buffers not freed, session state not reset
        return -1;
    }
    setup_timer();
    return 0;
}
// On retry, double-alloc or stale timer from previous attempt
```

**Detection**: For every error return path, verify ALL allocated resources and modified state are cleaned up.

### 3.4 Flag Not Cleared

```c
void handle_event() {
    if (event_pending) {
        process_event();
        // BUG: event_pending not cleared
        // Next call processes the same event again
    }
}
```

**Detection**: For every flag/boolean, trace all set/clear sites. Verify clear happens after processing.

---

## 4. Uninitialized Data

### 4.1 Stack Variable Depends on Prior Call

```c
void func() {
    int result;  // Uninitialized — value depends on stack content
    if (rare_condition)
        result = compute();
    return result;  // BUG: garbage if rare_condition is false
}
```

**Why intermittent**: Stack content changes with call history, making the garbage value sometimes "correct."

### 4.2 Struct Partial Init

```c
struct config cfg;
cfg.mode = MODE_A;
cfg.timeout = 5;
// BUG: cfg.flags uninitialized — may be 0 or garbage depending on stack
apply_config(&cfg);
```

### 4.3 Heap Content After Reuse

```c
ptr = malloc(size);
// BUG: heap memory may contain old data from previous allocation
// First allocation after program start: zeroed (from OS)
// Later allocations: contain freed data — may accidentally "work"
```

**Why intermittent**: Heap content depends on allocation/free history.

---

## 5. Resource Sensitivity

### 5.1 Memory Pressure

```c
ptr = malloc(large_size);
if (!ptr) {
    // Error path rarely tested
    // BUG: error handling code itself has a bug (NULL deref, leak)
}
```

**Why intermittent**: malloc failure only occurs under memory pressure.

### 5.2 FD Exhaustion

Low on file descriptors causes `open`/`socket`/`accept` to fail, triggering rarely-tested error paths.

### 5.3 Disk Full / Slow I/O

Write returns partial/error under disk pressure. Read takes longer than timeout.

### 5.4 CPU Load Affecting Timing

```c
set_alarm(100ms);  // Expect callback in ~100ms
// Under heavy CPU load, callback delayed to 500ms
// BUG: another timer already fired, state has changed
```

---

## 6. Environment & Configuration

### 6.1 Locale Dependence

```c
double val = atof("3.14");  // BUG: returns 3.0 in German locale (comma is decimal separator)
```

### 6.2 Timezone / Clock

```c
time_t now = time(NULL);
// BUG: during DST transition, time may jump forward/backward
// Interval calculation can go negative
```

### 6.3 Path / Permission

```c
// Works as root, fails as normal user
// Works in /home/user, fails in /tmp (different mount, sticky bit)
```

### 6.4 Network Latency / Packet Loss

```c
// Works on localhost, intermittent on real network
// Partial recv, EAGAIN, connection reset under packet loss
```

---

## 7. Analysis Strategy for Intermittent Bugs

### 7.1 The "What Changed?" Method

Compare successful and failed runs:
- **Same code, different result** → Look for: timing, state, uninitialized data, resources
- **Same inputs, different scheduling** → Race condition
- **Same everything, different time of day** → Timer/clock related
- **Works after reboot, fails after hours** → Resource leak or state accumulation

### 7.2 The "Hidden Precondition" Search

1. List everything that COULD differ between runs
2. For each candidate, check if it affects the failing code path
3. The hidden precondition is the factor that, when present, makes the bug deterministic

### 7.3 Stress Testing Approach

To increase reproduction rate:
- **Race conditions**: Run under heavy CPU load (`stress -c $(nproc)`)
- **Timing bugs**: Add artificial delays (`usleep`) at suspected race points
- **Memory bugs**: Run with `MALLOC_PERTURB_=165` (glibc) to make uninitialized reads fail faster
- **FD leaks**: Lower ulimit (`ulimit -n 32`)
- **Thread bugs**: Use ThreadSanitizer or Helgrind

### 7.4 Reproduction Rate as Diagnostic

| Reproduction Rate | Likely Category |
|-------------------|----------------|
| ~50% | Two-thread race with roughly equal timing |
| ~10-25% | Multi-factor race or timing window |
| ~1-5% | Narrow timing window or rare state combination |
| < 1% | Memory corruption manifest, ABA, or multi-condition convergence |
| "Only in production" | Load-dependent, resource-dependent, or environment-specific |
| "Only first time after boot" | Initialization order, cold cache, fresh state |
| "After running for hours" | State leak, resource leak, counter overflow |
