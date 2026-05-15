# Cross-Module Bug Analysis

Techniques for tracing logic bugs across module boundaries. Cross-module bugs are among the hardest to find because each module may appear correct in isolation.

## Table of Contents

1. [Interface Contract Verification](#1-interface-contract-verification)
2. [Shared State Auditing](#2-shared-state-auditing)
3. [Protocol & Message Verification](#3-protocol--message-verification)
4. [Data Flow Tracing](#4-data-flow-tracing)
5. [Common Cross-Module Bug Patterns](#5-common-cross-module-bug-patterns)

---

## 1. Interface Contract Verification

Every function call across modules is a contract. Both sides must agree.

### 1.1 Precondition Contract

| Check | Question |
|-------|----------|
| NULL parameters | Does caller guarantee non-NULL? Does callee verify? |
| Value ranges | Does caller guarantee valid range? Does callee validate? |
| State precondition | Does caller ensure module is initialized / in correct state? |
| Thread context | Does callee assume specific thread? Does caller comply? |
| Reentrancy | Can callee be called concurrently? Does caller protect? |

### 1.2 Postcondition Contract

| Check | Question |
|-------|----------|
| Return value meaning | Do caller and callee agree on what -1, 0, NULL mean? |
| Output parameter state | On error, is output parameter modified or unchanged? Both sides agree? |
| Side effects | Does callee modify global state? Does caller expect it? |
| Resource ownership | Who owns allocated memory/fd after the call? |

### 1.3 Error Contract

```c
// Module A: returns -1 on error, 0 on success
int module_a_init();

// Module B: assumes positive = success (POSIX-like)
if (module_a_init() > 0)  // BUG: 0 (success) is treated as failure
    proceed();
```

**Detection**: For cross-module calls, verify both sides agree on:
- Error return value convention (0=success? negative=error? NULL=error?)
- Whether errno is set
- Whether partial results are returned on error

---

## 2. Shared State Auditing

Systematically audit all state shared between modules.

### 2.1 Inventory

For the suspected bug region, list ALL shared state:

| State | Type | Writers | Readers | Protection |
|-------|------|---------|---------|------------|
| `g_config` | struct | config_module | all modules | rwlock |
| `msg_queue` | queue | producer_thread | consumer_thread | mutex+cond |
| `shared_mem` | mmap | process_A | process_B | semaphore |

### 2.2 Consistency Checks

For each shared state entry:

1. **Format agreement**: Do all accessors use the same struct definition, field layout, and packing?
2. **Semantic agreement**: Do all accessors interpret field values the same way?
3. **Lifecycle agreement**: Who creates it? Who destroys it? Is there a use-after-destroy risk?
4. **Synchronization**: Is the protection mechanism actually used at ALL access sites?
5. **Atomicity**: Are multi-field updates atomic? (If reader sees half-updated state = bug)
6. **Ordering**: Are there memory barriers between dependent writes? (flag + data pattern)

### 2.3 The Flag + Data Pattern (Common Bug)

```c
// Writer (Module A):
data_buf[0..N] = payload;
ready_flag = 1;           // Without memory barrier, CPU may reorder

// Reader (Module B):
if (ready_flag) {
    process(data_buf);     // BUG: may see stale data_buf despite ready_flag == 1
}
```

**Fix**: Memory barrier between data write and flag write. On x86 often works by accident (strong memory model); on ARM/MIPS fails (weak memory model).

---

## 3. Protocol & Message Verification

### 3.1 Message Structure Verification

```
For each message type exchanged between modules:
1. Compare struct definition on sender and receiver side
2. Verify #pragma pack / __attribute__((packed)) match
3. Verify sizeof() matches on both sides
4. Verify field byte order (endianness) for cross-arch
5. Verify field alignment for cross-platform
```

### 3.2 Message Sequence Verification

```
For each protocol sequence:
1. Does sender guarantee ordering? (TCP yes, UDP no, message queue depends)
2. Can messages be duplicated? (network retry, message queue re-delivery)
3. Can messages be lost? (UDP, unreliable IPC)
4. Is there a sequence number? Is it checked?
5. What happens when an unexpected message arrives? (wrong state, wrong sequence)
```

### 3.3 Message Boundary Verification

```c
// Sender:
char msg[64];
fill_message(msg, 64);
send(fd, msg, 64, 0);

// Receiver:
char buf[64];
int n = recv(fd, buf, 64, 0);
// BUG: n may be < 64 (partial recv on TCP)
// BUG: n may contain parts of next message (TCP stream, no framing)
```

**Detection**: Verify message framing protocol. Check all recv/read for partial handling.

---

## 4. Data Flow Tracing

### 4.1 End-to-End Data Tracing

For the buggy data/value, trace its entire journey:

```
Source (user input / sensor / config / calculation)
  → Transform 1 (Module A: parse, convert, validate)
    → Storage (global variable / queue / shared memory)
      → Transform 2 (Module B: read, interpret, compute)
        → Sink (output / hardware / display / decision)
```

At each step, verify:
- Is the value format what the next step expects?
- Is the value range what the next step expects?
- Is the value's unit what the next step expects?
- Is the value fresh (not stale from previous operation)?

### 4.2 Value Provenance Tracking

When a wrong value appears, trace backwards:

1. Where is this value assigned? (immediate source)
2. Where does that value come from? (one level up)
3. Continue until reaching external input or constant
4. At each level, verify the transformation is correct

### 4.3 Cross-Module Print Strategy

To diagnose, add prints at module boundaries:

```c
// At Module A output:
DBG("[A→B] msg_type=%d field1=%d field2=%s checksum=0x%x",
    msg.type, msg.field1, msg.field2, msg.checksum);

// At Module B input:
DBG("[B←A] msg_type=%d field1=%d field2=%s checksum=0x%x",
    msg.type, msg.field1, msg.field2, msg.checksum);

// Compare the two — any difference reveals:
// - Transmission corruption
// - Endianness issue
// - Struct padding difference
// - Partial send/recv
```

---

## 5. Common Cross-Module Bug Patterns

### 5.1 API Behavior Change Without Notification

Module A updates its API behavior (e.g., return value meaning changes, new error code added). Module B still uses old assumptions.

**Detection**: Check versioning, changelogs, and git blame on the interface definition.

### 5.2 Header File Version Mismatch

Module A and B compiled with different versions of a shared header:
- struct size differs → memory corruption
- enum values differ → wrong dispatch
- macro definitions differ → different code paths

**Detection**: Verify all modules include identical header versions. Check build system for consistency.

### 5.3 Initialization Dependency Not Enforced

Module B calls Module A's API before Module A is initialized:
- Global state is zero/NULL → might work by accident (zero is often a valid default)
- Or crashes in rare cases when zero is NOT valid

**Detection**: Trace startup sequence. Verify explicit init ordering or lazy-init guards.

### 5.4 Shutdown Order Bug

Module A deinits while Module B still references A's resources:
- A frees its data structures
- B's next call to A → use-after-free or crash

**Detection**: Verify shutdown order is reverse of init order. Check for pending callbacks/timers that reference deinited modules.

### 5.5 Config Propagation Delay

Config is changed in one module but other modules don't see the update until they re-read:
- Module A updates config value
- Module B cached the old value at startup
- BUG: Module B uses stale config forever

**Detection**: Check if config changes trigger notifications to all consumers, or if consumers re-read periodically.

### 5.6 Error Propagation Failure

```c
// Module A encounters error, returns -1
int ret = module_a_operation();
// Module B ignores error, continues with invalid data
if (ret != 0)
    log("warning");  // Logs but doesn't stop — continues with corrupt state
module_b_process(data);  // data is invalid because module_a_operation failed
```

**Detection**: Trace error returns across module boundaries. Verify each error is either handled or propagated, never just logged-and-ignored.

---

## 6. Feature Modification Ripple Effect Analysis

When modifying Feature A introduces bugs in Feature B. This is the "fix A, break B" problem.

### 6.1 Ripple Effect Detection Workflow

When a bug report says "Feature B broke after Feature A was modified":

1. **Diff Analysis**: Get the exact changes made for Feature A
2. **Shared Touchpoint Scan**:
   - List every function, struct, global, constant, config touched by the diff
   - For each, find ALL other consumers using grep/code search
   - Filter to consumers belonging to Feature B or shared infrastructure
3. **Impact Classification**:

   | Touchpoint Type | Impact on Feature B |
   |----------------|--------------------|
   | Shared function behavior changed | B calls same function, gets different result |
   | Shared struct layout changed | B's binary access is wrong, serialization broken |
   | Global state timing/value changed | B reads state at wrong time or wrong value |
   | Condition broadened/narrowed | B's inputs now take a different code path |
   | Resource limit changed | B exceeds new limit, was within old limit |
   | Init/shutdown order changed | B's dependencies not met at call time |
   | Error path changed | B's cleanup/recovery code now skipped |
   | Performance changed | B's latent race condition exposed |

4. **Verification**: For each impacted touchpoint:
   - Trace Feature B's code path through the modified code
   - Simulate with B's typical inputs — does it still produce correct results?
   - Check B's edge cases through the new path

### 6.2 Cross-Feature Shared Code Audit

When multiple features share utility functions, data structures, or infrastructure:

```
For each shared component in the diff:
  1. List ALL features that depend on it
  2. For each feature:
     a. What behavior does this feature expect from the shared component?
     b. Does the modification preserve that behavior?
     c. Test with feature-specific inputs through the new code path
  3. If behavior changed:
     a. Can the shared component be made configurable per-feature?
     b. Should the shared component be split into feature-specific versions?
     c. Can a compatibility wrapper preserve old behavior for unchanged features?
```

### 6.3 Cross-Feature Print Strategy

When investigating Feature A → Feature B ripple effect:

```c
// At the shared touchpoint, print which feature is calling:
DBG("[SHARED] %s called by: %s, args: x=%d y=%d",
    __func__, caller_feature_name, x, y);

// Before and after Feature A's change, in Feature B's path:
DBG("[B] before shared_func: state=%d expect_result=%d", b_state, expected);
int result = shared_function(args);
DBG("[B] after shared_func: result=%d (expected %d) %s",
    result, expected, result == expected ? "OK" : "MISMATCH!");
```

This immediately reveals if Feature A's modification changed the shared function's behavior for Feature B's inputs.
