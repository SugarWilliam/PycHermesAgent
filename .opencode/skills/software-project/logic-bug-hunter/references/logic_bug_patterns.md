# Logic Bug Patterns

Exhaustive categorization of logic bug patterns with detection methods, code examples, and root cause explanations. Reference when forming hypotheses during logic bug analysis.

## Table of Contents

1. [Condition & Branch Errors](#1-condition--branch-errors)
2. [Calculation & Data Flow Errors](#2-calculation--data-flow-errors)
3. [State Machine & Lifecycle Errors](#3-state-machine--lifecycle-errors)
4. [Requirement-Implementation Mismatches](#4-requirement-implementation-mismatches)
5. [Cross-Module Logic Errors](#5-cross-module-logic-errors)
6. [Boundary & Edge Case Errors](#6-boundary--edge-case-errors)
7. [Control Flow Errors](#7-control-flow-errors)
8. [Type & Conversion Errors](#8-type--conversion-errors)
9. [Feature Modification Ripple Effects](#9-feature-modification-ripple-effects)

---

## 1. Condition & Branch Errors

### 1.1 Inverted Condition

**Symptom**: Exact opposite behavior from expected.

```c
// BUG: should be !is_valid
if (is_valid)
    return -EINVAL;
```

**Detection**: For every `if`/`else`, ask: "Does the true-branch match the condition semantics?"

### 1.2 Wrong Comparison Operator

```c
// BUG: should be >= (fails when index exactly equals array_size)
if (index > array_size)
    return ERROR;

// BUG: should be < (writes one past end)
for (int i = 0; i <= count; i++)
    buf[i] = data[i];
```

**Operators to double-check**: `<` vs `<=`, `>` vs `>=`, `==` vs `!=`, `=` vs `==`

### 1.3 Wrong Logical Operator

```c
// BUG: should be || (both conditions prevent action, either should trigger)
if (no_permission && quota_exceeded)
    deny_request();

// BUG: operator precedence — & binds tighter than &&
if (flags & FLAG_A && flags & FLAG_B)
    // Parsed as: flags & (FLAG_A && flags) & FLAG_B
```

**Detection**: For compound conditions, mentally evaluate with concrete values. Check if `&&`/`||` matches the requirement (ALL vs ANY).

### 1.4 Missing Condition / Dead Branch

```c
switch (msg_type) {
    case MSG_START: handle_start(); break;
    case MSG_STOP:  handle_stop();  break;
    // BUG: MSG_PAUSE not handled — silently dropped
}

// BUG: condition can never be true (dead code)
if (unsigned_var < 0)
    handle_error();
```

**Detection**: Enumerate ALL possible input values/states. Check each has a corresponding code path. Check for tautologies and contradictions.

### 1.5 Short-Circuit Side Effect

```c
// BUG: when ptr is NULL, validate() is never called — side effect skipped
if (ptr != NULL && validate(ptr))
    process(ptr);
// If validate() also sets a flag needed later, logic is broken
```

**Detection**: Check if right-hand side of `&&`/`||` has needed side effects.

### 1.6 Condition Copy-Paste Error

```c
if (a > threshold_a)
    handle_a();
else if (a > threshold_b)  // BUG: should be b > threshold_b (copy-paste from above)
    handle_b();
```

**Detection**: In chained if-else, verify each condition uses the correct variable.

---

## 2. Calculation & Data Flow Errors

### 2.1 Wrong Variable Used

```c
// BUG: should be height, not width (copy-paste)
int area = width * width;

// BUG: using stale variable instead of updated one
new_val = compute(old_val);
result = transform(old_val);  // Should use new_val
```

**Detection**: For every formula/expression, verify each variable name matches the semantic intent.

### 2.2 Wrong Unit / Scale

```c
// BUG: timeout is in ms, but sleep expects seconds
sleep(timeout_ms);  // Sleeps 1000x too long

// BUG: sensor returns millivolts, code treats as volts
if (voltage > 5)  // Never triggers because voltage is e.g. 3300
    over_voltage_alert();
```

**Detection**: At every interface boundary, verify unit consistency. Document units in variable names: `timeout_ms`, `voltage_mv`.

### 2.3 Integer Overflow / Underflow

```c
// BUG: overflow if count and size are large
size_t total = count * elem_size;
void *buf = malloc(total);  // Allocates tiny buffer due to overflow

// BUG: unsigned underflow wraps to huge value
unsigned remaining = total - used;  // If used > total, wraps to ~4 billion
```

**Detection**: At every arithmetic site, check if operands can cause overflow. Especially: multiplication for allocation, unsigned subtraction, left shift.

### 2.4 Floating Point Comparison

```c
// BUG: floating point should not be compared with ==
if (result == 0.1)
    // May never be true due to FP representation
```

**Detection**: Find `==` / `!=` on float/double. Use epsilon comparison instead.

### 2.5 Operator Precedence Error

```c
// BUG: + has higher precedence than <<
int result = base + offset << shift;
// Parsed as: (base + offset) << shift
// Intended:  base + (offset << shift)
```

**Common traps**: `&` vs `&&`, `|` vs `||`, `<<`/`>>` vs `+`/`-`, `?:` vs `=`

---

## 3. State Machine & Lifecycle Errors

### 3.1 Missing State Transition

```c
// BUG: no transition defined for EVENT_TIMEOUT in STATE_CONNECTING
// System stays stuck in CONNECTING forever
switch (state) {
    case STATE_CONNECTING:
        if (event == EVENT_CONNECTED) state = STATE_READY;
        // Missing: EVENT_TIMEOUT → STATE_IDLE
        break;
}
```

**Detection**: Build full state×event matrix. Check every cell has a defined action.

### 3.2 Invalid State Transition

```c
// BUG: allows IDLE → STOPPING (should only go RUNNING → STOPPING)
if (event == EVENT_STOP)
    state = STATE_STOPPING;  // No guard on current state
```

**Detection**: For each transition, verify the source state is valid.

### 3.3 State Not Reset on Error / Re-entry

```c
static int retry_count = 0;
void start_transfer() {
    // BUG: retry_count not reset on new transfer
    // If previous transfer used 2 retries, new transfer starts at 2
    if (retry_count >= MAX_RETRIES)
        return FAIL;
    retry_count++;
    do_transfer();
}
```

**Detection**: Check all `static`/global state variables — are they reset on re-entry, error exit, and module restart?

### 3.4 Cleanup Not Done on State Change

```c
void change_mode(int new_mode) {
    // BUG: resources from old mode not released
    // Timer still running, buffer still allocated
    current_mode = new_mode;
    init_mode(new_mode);
}
```

**Detection**: For each state transition, verify old state's resources are cleaned up.

### 3.5 Double Initialization / Double Cleanup

```c
// BUG: init called twice without deinit — resource leak or corruption
if (need_restart)
    module_init();  // Already initialized from startup
```

**Detection**: Check if init/deinit are idempotent or if they're guarded against double-call.

---

## 4. Requirement-Implementation Mismatches

### 4.1 Feature Not Implemented

The code simply doesn't implement what the requirement asks. No code path exists for the feature.

**Detection**: Map each requirement → code. Report requirements with no corresponding implementation.

### 4.2 Partially Implemented

```c
// Requirement: "Support A, B, and C modes"
switch (mode) {
    case MODE_A: handle_a(); break;
    case MODE_B: handle_b(); break;
    // MODE_C not implemented
}
```

**Detection**: Compare all specified behaviors against code. Check for TODO/FIXME comments near partial implementations.

### 4.3 Implemented But With Wrong Logic

```c
// Requirement: "Sort by priority descending (highest first)"
// BUG: sorts ascending
qsort(items, count, sizeof(item_t), compare_priority_asc);
```

**Detection**: Trace the actual behavior step by step and compare against the requirement's expected behavior at every step.

### 4.4 Extra Unintended Behavior

```c
// Requirement: "Reset counter on mode change"
void change_mode(int new_mode) {
    counter = 0;
    history_clear();  // BUG: requirement didn't ask to clear history
}
```

**Detection**: Check if code does MORE than the requirement specifies — unintended side effects.

### 4.5 Edge Case Not Specified

The requirement is silent on what happens at boundaries. The code picks a behavior, but it may not match user expectations.

**Detection**: Identify boundary conditions (empty input, max value, concurrent access). Check if requirement specifies handling. If not, flag as ambiguity.

---

## 5. Cross-Module Logic Errors

### 5.1 Struct Field Semantic Mismatch

```c
// Module A: length field means "total length including header"
msg.length = header_size + payload_size;

// Module B: assumes length means "payload length only"
char *payload = malloc(msg.length);  // BUG: over-allocates
memcpy(payload, msg.data, msg.length);  // BUG: copies header into payload
```

**Detection**: Compare struct field usage across all modules that touch it.

### 5.2 Enum / Constant Value Drift

```c
// header_v1.h: enum { CMD_START=0, CMD_STOP=1, CMD_PAUSE=2 }
// header_v2.h: enum { CMD_START=0, CMD_PAUSE=1, CMD_STOP=2 }
// BUG: module A uses v1, module B uses v2 — PAUSE and STOP swapped
```

**Detection**: Search for duplicate enum/constant definitions. Compare values across all definition sites.

### 5.3 Protocol / Message Format Mismatch

```c
// Sender packs: [type(4B)][length(4B)][payload(NB)]
// Receiver expects: [type(2B)][length(2B)][payload(NB)]
// BUG: receiver reads wrong offsets for everything after type
```

**Detection**: Verify struct definition, packing (#pragma pack), and sizeof match on both ends.

### 5.4 Callback Contract Violation

```c
// Module A registers callback expecting it runs in thread context:
register_callback(my_handler);

// Module B calls the callback from ISR / timer / signal handler:
// BUG: my_handler calls malloc, mutex_lock — unsafe in those contexts
```

**Detection**: For every callback, verify the calling context matches what the callback implementation assumes.

### 5.5 Shared State Without Agreement

```c
// Module A sets flag after completing operation:
operation_done = 1;

// Module B checks flag AND assumes data buffer is valid when flag is set:
if (operation_done)
    process(data_buf);
// BUG: Module A sets flag but hasn't filled data_buf yet (ordering)
// Or: no memory barrier between flag write and data write
```

**Detection**: For every shared variable, verify ALL invariants that readers assume are guaranteed by writers.

---

## 6. Boundary & Edge Case Errors

### 6.1 Off-By-One

```c
// BUG: should be < len, not <= len
for (int i = 0; i <= len; i++)
    array[i] = 0;  // Writes past end when i == len
```

**Variants**: Array bounds, string terminator position, first/last element, loop count, buffer size.

### 6.2 Empty / Zero / NULL Input

```c
// BUG: crashes when list is empty (count = 0)
result = list[count - 1];  // Array index -1 when count is 0

// BUG: division by zero not checked
average = total / count;
```

**Detection**: For every function, test mental execution with zero/empty/NULL inputs.

### 6.3 Maximum / Overflow Boundary

```c
// BUG: sequence wraps from 0xFFFF to 0x0000
uint16_t seq_num;
if (new_seq > last_seq)  // Fails when new_seq wrapped
    process_in_order();
```

**Detection**: Check each variable's type limits and whether wrap-around is handled.

### 6.4 First-Time / Last-Time Special Case

```c
// BUG: first call has prev_value uninitialized
static int prev_value;
int delta = current_value - prev_value;  // Garbage on first call
prev_value = current_value;
```

**Detection**: Check first invocation and last invocation for special-case handling.

---

## 7. Control Flow Errors

### 7.1 Missing Break in Switch

```c
case CMD_A:
    handle_a();
    // BUG: falls through to CMD_B
case CMD_B:
    handle_b();
    break;
```

### 7.2 Premature Return in Loop

```c
// BUG: return should be continue — only processes first matching item
for (int i = 0; i < count; i++) {
    if (items[i].type == TARGET) {
        process(items[i]);
        return;  // Should be: continue; or break after accumulating
    }
}
```

### 7.3 Wrong Loop Variable Modified

```c
// BUG: outer loop variable modified in inner loop
for (int i = 0; i < rows; i++) {
    for (int j = 0; j < cols; j++) {
        if (condition)
            i++;  // BUG: modifies outer loop counter
    }
}
```

### 7.4 Infinite Loop Due to Wrong Exit Condition

```c
// BUG: unsigned can never be < 0
unsigned int i = start;
while (i >= 0) {  // Always true for unsigned
    process(i);
    i--;
}
```

### 7.5 Goto Skips Initialization

```c
if (error)
    goto cleanup;
int *buf = malloc(size);  // Skipped by goto
// ...
cleanup:
    free(buf);  // BUG: buf not initialized if goto was taken
```

---

## 8. Type & Conversion Errors

### 8.1 Signed / Unsigned Mismatch

```c
int len = get_length();     // Could return -1 for error
unsigned idx = some_index;
if (idx < len)              // BUG: -1 becomes huge unsigned, comparison always false
    process(array[idx]);
```

### 8.2 Implicit Narrowing Truncation

```c
uint32_t full_value = 0x12345678;
uint16_t truncated = full_value;  // Silently becomes 0x5678
// BUG if full_value is expected to be preserved
```

### 8.3 Format String / Argument Type Mismatch

```c
uint64_t big = 0xFFFFFFFFFFULL;
printf("value = %d\n", big);  // BUG: %d for uint64_t — prints wrong value
// Correct: printf("value = %llu\n", (unsigned long long)big);
```

### 8.4 Pointer Type Confusion

```c
int *int_ptr = (int *)char_buf;
*int_ptr = value;  // BUG: may violate alignment rules on ARM/MIPS → SIGBUS
// Also: reads 4 bytes but caller expects char access pattern
```

### 8.5 Sizeof Confusion

```c
// BUG: sizeof pointer (8 bytes on 64-bit) instead of sizeof struct
struct msg *p = malloc(sizeof(p));  // Should be sizeof(*p) or sizeof(struct msg)

// BUG: sizeof array decays to sizeof pointer in function parameter
void clear(int arr[]) {
    memset(arr, 0, sizeof(arr));  // Only clears 8 bytes on 64-bit
}
```

---

## 9. Feature Modification Ripple Effects

Modifying Feature A may break Feature B due to shared code, shared state, implicit dependencies, or global side effects. This category captures "fix A, break B" bugs.

### 9.1 Shared Function Modified for A, Breaks B

```c
// Shared utility used by both feature A and feature B:
int parse_message(const char *buf, int len) {
    // Original: returns payload length
    // Modified for Feature A: now returns total length (header + payload)
    return header_size + payload_size;  // Feature A needs this
}

// Feature B (unchanged, still expects payload length):
int payload_len = parse_message(buf, len);
char *payload = malloc(payload_len);       // BUG: over-allocates
memcpy(payload, buf + HEADER_SIZE, payload_len);  // BUG: reads past end
```

**Detection**:
1. For every modified function, find ALL callers (not just the ones related to Feature A)
2. Verify every other caller still receives the behavior it expects
3. Pay special attention to return value semantics, output parameter contents, and side effects

### 9.2 Shared Data Structure Modified for A, Breaks B

```c
// Feature A needs a new field, modifies shared struct:
struct session {
    int state;
    int mode;        // Feature A adds this field
    char buf[128];   // Feature B accesses this — offset shifted!
};

// Feature B uses binary offset or sizeof assumptions:
memcpy(dst, &session + offsetof(struct session, buf), 128);
// BUG: if B was compiled with old header, offsetof(buf) is wrong

// Or: Feature B relies on struct size for serialization:
send(fd, &session, sizeof(old_session_t), 0);  // BUG: truncates new field or
                                                 //       sends wrong size
```

**Detection**:
1. For every modified struct/class, find ALL files that use it
2. Check if all modules are recompiled with the new header
3. Check serialization, IPC, and persistent storage that embed struct layout
4. Check `sizeof`, `offsetof`, hardcoded sizes, and binary-level access

### 9.3 Global / Static State Side Effect

```c
// Feature A modification changes when/how a global flag is set:
void feature_a_handler() {
    // Previously: set g_system_ready = 1 at end
    // Now: set g_system_ready = 1 at beginning (for Feature A's new fast-path)
    g_system_ready = 1;
    do_slow_initialization();  // Not done yet when flag is set
}

// Feature B checks g_system_ready and proceeds:
void feature_b_handler() {
    if (g_system_ready)
        use_initialized_resources();  // BUG: resources not ready yet
}
```

**Detection**:
1. List ALL global/static variables modified by the changed code
2. For each, find ALL readers across the entire codebase
3. Check if the timing, value, or semantics of the modification changed
4. Verify all readers' assumptions still hold with the new modification pattern

### 9.4 Condition / Branch Change Alters Shared Path

```c
// Shared code path, Feature A changes the condition:
if (mode == MODE_X || mode == MODE_Y) {  // Was: if (mode == MODE_X)
    setup_fast_path();
    process();
}

// Feature B relies on MODE_Y NOT entering fast_path:
// BUG: MODE_Y now goes through fast_path, which doesn't handle B's state
// Feature B breaks because setup_fast_path() clobbers B's context
```

**Detection**:
1. For every modified condition, evaluate the change's effect on ALL possible input values
2. Identify which values NOW enter a path they didn't before (or vice versa)
3. Verify the new path is valid for those values in the context of ALL features

### 9.5 Resource Contention After A's Change

```c
// Feature A changes buffer size or allocation strategy:
#define SHARED_BUF_SIZE 1024  // Was: 4096

// Feature B writes up to 4096 bytes into shared buffer:
// BUG: buffer overflow after A reduced the size
memcpy(shared_buf, data, data_len);  // data_len can be up to 4096
```

**Detection**:
1. For every modified constant, buffer size, pool size, or resource limit, find ALL users
2. Verify all users can operate within the new limits
3. Check for hardcoded sizes elsewhere that assumed the old value

### 9.6 Execution Order / Initialization Change

```c
// Feature A moves its initialization earlier for performance:
void system_init() {
    feature_a_init();  // Moved from after feature_c_init to before feature_b_init
    feature_b_init();  // B depended on A NOT being initialized yet
    feature_c_init();  // C depended on A being initialized (still works)
}

// Feature B's init registered a callback that feature_a_init now invokes:
// BUG: callback fires during B's init, B's internal state is incomplete
```

**Detection**:
1. If initialization, cleanup, or event ordering changed, map ALL dependencies
2. Check if any module depends on being initialized before/after the modified module
3. Check callbacks and event hooks that fire during initialization — are all handlers ready?

### 9.7 Error Handling Change Affects Recovery Path

```c
// Feature A changes error handling — now returns early instead of falling through:
int shared_operation() {
    ret = step_one();
    if (ret < 0)
        return ret;  // NEW: early return for Feature A's error path
    // Feature B's cleanup code below is now skipped:
    feature_b_cleanup_partial_state();
    return ret;
}
```

**Detection**:
1. For every new `return`/`goto`/`break` added to shared code, check what code is now skipped
2. Verify no other feature depends on the skipped code executing
3. Pay special attention to cleanup, notification, and state-reset code after the new exit point

### 9.8 Timing / Performance Change Triggers Latent Bug

```c
// Feature A optimizes processing — completes 10x faster:
void feature_a_process() {
    // Previously took ~100ms, now takes ~10ms
    fast_algorithm(data);
    notify_done();
}

// Feature B has a race condition that was hidden by A's slow execution:
// The 100ms processing time effectively serialized A and B
// BUG: now A finishes before B starts its critical section,
//       exposing a race on shared_resource that was always there
```

**Detection**:
1. Performance improvements can expose latent concurrency bugs
2. If Feature A's timing changed significantly, check all concurrent operations that "happened to work" due to the old timing
3. Check if any module relies on implicit ordering from execution duration rather than explicit synchronization

### 9.9 Feature Toggle / Config Change Affects Shared Code Path

```c
// Feature A introduces a config flag that changes behavior:
if (config.feature_a_v2_enabled) {
    new_processing();  // New path for Feature A
} else {
    old_processing();  // Legacy path
}

// BUG: new_processing() skips a side effect that Feature B depends on:
// old_processing() called notify_state_change() internally
// new_processing() does not — Feature B never gets the notification
```

**Detection**:
1. For feature toggles, verify BOTH paths (enabled AND disabled) maintain all side effects other features depend on
2. Diff the old and new code paths — list all functions called in old but not in new (and vice versa)
3. For each missing call, check if any other module depends on it

### Ripple Effect Detection Strategy

When analyzing any code modification, apply this systematic scan:

1. **Impact Inventory**: List everything the modification touches:
   - Functions modified (and ALL their callers)
   - Data structures modified (and ALL their users)
   - Global/static state modified (and ALL readers/writers)
   - Constants/macros modified (and ALL references)
   - Conditions modified (and ALL affected input values)
   - Resource limits modified (and ALL consumers)
   - Execution order modified (and ALL order-dependent modules)
   - Error paths modified (and ALL downstream cleanup)

2. **Cross-Feature Verification**: For each impacted item:
   - Does this item serve other features besides the one being modified?
   - Do those other features still receive correct behavior?
   - Were implicit assumptions (timing, ordering, values) broken?

3. **Regression Indicators**:
   - "Feature B used to work before Feature A was changed" → Classic ripple effect
   - "The bug appears only when Feature A is enabled" → Feature toggle side effect
   - "Works on old version, broken on new version with A's patch" → Shared code contamination
   - "B works if we revert A's change" → Direct causal link, trace A's diff for shared touchpoints
