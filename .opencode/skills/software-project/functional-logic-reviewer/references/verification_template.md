# Detailed Verification Checklist

Comprehensive checklist for functional logic verification of embedded Linux code changes. Use for manual test planning after AI review.

## 1. Functional Verification

### 1.1 Business Requirement Alignment

| Check | Description | Status |
|-------|-------------|--------|
| Changelog Match | Code change matches the described requirement | ☐ |
| Complete Implementation | All described features are implemented | ☐ |
| No Extra Changes | No unintended functionality added | ☐ |
| API Contract | Function signatures and return values correct | ☐ |

### 1.2 Logic Correctness

| Check | Description | Status |
|-------|-------------|--------|
| Condition Logic | if/else conditions are correct | ☐ |
| Loop Logic | Loop termination conditions are correct | ☐ |
| Switch Cases | All cases are covered, no fallthrough issues | ☐ |
| Return Values | All return paths return correct values | ☐ |

## 2. State Machine Analysis

### 2.1 State Definition

| Check | Description | Status |
|-------|-------------|--------|
| Initial State | Initial state is clearly defined | ☐ |
| Valid States | All states are valid and meaningful | ☐ |
| Final State | Final/terminal state is defined | ☐ |
| State Count | Number of states is appropriate | ☐ |

### 2.2 State Transitions

| Check | Description | Status |
|-------|-------------|--------|
| Transition Rules | All transition rules are defined | ☐ |
| Valid Transitions | Each transition is valid and safe | ☐ |
| Missing Transitions | No required transitions are missing | ☐ |
| Illegal Transitions | No transitions to invalid states | ☐ |
| Transition Completeness | All paths through state machine are covered | ☐ |

### 2.3 State Handling

| Check | Description | Status |
|-------|-------------|--------|
| State Persistence | State is correctly persisted if needed | ☐ |
| State Recovery | Can recover from state loss/corruption | ☐ |
| Concurrent Access | Concurrent state access is protected | ☐ |

## 3. Boundary Conditions

### 3.1 Input Validation

| Check | Description | Status |
|-------|-------------|--------|
| NULL Checks | All pointers checked before use | ☐ |
| Empty Input | Empty input is handled correctly | ☐ |
| Zero Values | Division by zero is prevented | ☐ |
| Negative Values | Negative values in unsigned contexts | ☐ |
| Overflow | Integer overflow is handled | ☐ |
| Underflow | Integer underflow is handled | ☐ |
| Special Values | NaN, infinity, special floats handled | ☐ |

### 3.2 Array/List Bounds

| Check | Description | Status |
|-------|-------------|--------|
| Index Range | Array index within bounds | ☐ |
| Size Check | Size checks before access | ☐ |
| Empty Container | Empty container handled correctly | ☐ |
| Iterator Validity | Iterator invalidation prevented | ☐ |

### 3.3 String Operations

| Check | Description | Status |
|-------|-------------|--------|
| Buffer Size | Buffer large enough for input | ☐ |
| Null Termination | Strings are null-terminated | ☐ |
| Encoding | Character encoding is handled | ☐ |
| Truncation | String truncation is handled gracefully | ☐ |

## 4. Timing & Concurrency

### 4.1 Lock Management

| Check | Description | Status |
|-------|-------------|--------|
| Lock Order | Consistent lock ordering to prevent deadlock | ☐ |
| Lock Scope | Critical section is properly scoped | ☐ |
| Lock Type | Correct lock type for the situation | ☐ |
| Lock Release | All code paths release the lock | ☐ |

### 4.2 Race Conditions

| Check | Description | Status |
|-------|-------------|--------|
| Shared Access | All shared data accesses are protected | ☐ |
| Atomic Operations | Compound operations are atomic | ☐ |
| Double-Check | Double-checked locking pattern correct | ☐ |
| Publication | Safe publication of shared objects | ☐ |

### 4.3 Async Operations

| Check | Description | Status |
|-------|-------------|--------|
| Order | Async operations have correct order | ☐ |
| Completion | All async operations complete | ☐ |
| Timeout | Timeout handling is correct | ☐ |
| Cancellation | Cancellation is handled correctly | ☐ |
| Dependencies | Async dependencies are correct | ☐ |

### 4.4 Thread Safety

| Check | Description | Status |
|-------|-------------|--------|
| Thread-Local | Thread-local data is correctly marked | ☐ |
| Reentrancy | Reentrant functions are safe | ☐ |
| Signal Safety | Signal handlers are async-signal-safe | ☐ |

## 5. Configuration Consistency

### 5.1 Configuration Management

| Check | Description | Status |
|-------|-------------|--------|
| Single Source | Single source of truth for each config | ☐ |
| Default Values | Default values are correct | ☐ |
| Override Order | Override order is correct | ☐ |
| Persistence | Config is persisted correctly | ☐ |

### 5.2 Consistency Checks

| Check | Description | Status |
|-------|-------------|--------|
| Cross-Module | Config consistent across modules | ☐ |
| Runtime/Compile | Runtime and compile-time config aligned | ☐ |
| Version | Config version is checked | ☐ |
| Migration | Config migration path exists | ☐ |

### 5.3 Hardcoded Values

| Check | Description | Status |
|-------|-------------|--------|
| Magic Numbers | No magic numbers (use constants) | ☐ |
| Hardcoded Paths | No hardcoded paths | ☐ |
| Hardcoded Time | No hardcoded timeouts/delays | ☐ |

## 6. Exception Handling

### 6.1 Error Detection

| Check | Description | Status |
|-------|-------------|--------|
| Error Returns | All error conditions return errors | ☐ |
| Error Codes | Error codes are specific enough | ☐ |
| Error Propagation | Errors are propagated correctly | ☐ |

### 6.2 Error Recovery

| Check | Description | Status |
|-------|-------------|--------|
| Retry Logic | Retry is implemented where appropriate | ☐ |
| Fallback | Fallback behavior is correct | ☐ |
| Degradation | Graceful degradation is implemented | ☐ |

### 6.3 Resource Cleanup

| Check | Description | Status |
|-------|-------------|--------|
| Memory | Memory is freed in all paths | ☐ |
| File Handles | File handles are closed | ☐ |
| Locks | Locks are released | ☐ |
| Connections | Network connections are closed | ☐ |
| Temporary Files | Temp files are deleted | ☐ |

### 6.4 Logging

| Check | Description | Status |
|-------|-------------|--------|
| Error Logging | Errors are logged with context | ☐ |
| No Sensitive Data | No sensitive data in logs | ☐ |
| Log Level | Appropriate log levels used | ☐ |

## 7. Impact Analysis

### 7.1 Module Dependencies

| Check | Description | Status |
|-------|-------------|--------|
| Caller Impact | All callers are identified | ☐ |
| Callee Impact | Callee changes are correct | ☐ |
| Side Effects | No unintended side effects | ☐ |
| API Compatibility | Backward compatibility maintained | ☐ |

### 7.2 Performance Impact

| Check | Description | Status |
|-------|-------------|--------|
| Time Complexity | Algorithm complexity is acceptable | ☐ |
| Memory Usage | Memory usage is bounded | ☐ |
| I/O Operations | I/O is minimized/batched | ☐ |
| Lock Contention | Lock contention is low | ☐ |

### 7.3 Compatibility

| Check | Description | Status |
|-------|-------------|--------|
| ABI Compatibility | No ABI breaks | ☐ |
| API Compatibility | No API breaks | ☐ |
| Data Compatibility | Data format compatible | ☐ |
| Protocol Compatibility | Protocol version handled | ☐ |

## 8. Security Considerations

### 8.1 Input Security

| Check | Description | Status |
|-------|-------------|--------|
| Injection | No injection vulnerabilities | ☐ |
| Overflows | Buffer overflows prevented | ☐ |
| Validation | All input is validated | ☐ |
| Sanitization | Input is sanitized | ☐ |

### 8.2 Access Control

| Check | Description | Status |
|-------|-------------|--------|
| Authentication | Authentication is required | ☐ |
| Authorization | Authorization is checked | ☐ |
| Least Privilege | Principle of least privilege followed | ☐ |

### 8.3 Data Protection

| Check | Description | Status |
|-------|-------------|--------|
| Encryption | Sensitive data encrypted | ☐ |
| Masking | Sensitive data masked in logs | ☐ |
| Secure Storage | Secrets stored securely | ☐ |

## 9. Embedded Linux Specifics

### 9.1 DMA & Memory-Mapped I/O

| Check | Description | Status |
|-------|-------------|--------|
| DMA Alignment | DMA buffers cache-line aligned | ☐ |
| Cache Coherency | sync_for_cpu/sync_for_device called | ☐ |
| MMIO Access | readl/writel used (not raw pointer) | ☐ |
| Memory Barriers | wmb/rmb around HW register sequences | ☐ |
| mmap Alignment | offset/size page-aligned | ☐ |

### 9.2 Interrupt & Atomic Context

| Check | Description | Status |
|-------|-------------|--------|
| ISR Duration | ISR is minimal (ack + schedule bottom half) | ☐ |
| No Sleep in ISR | No mutex/kmalloc(GFP_KERNEL)/sleep in ISR | ☐ |
| Shared ISR Data | volatile/READ_ONCE or spin_lock_irqsave | ☐ |
| Spinlock Context | No sleeping function under spinlock | ☐ |
| IRQ Enable/Disable | Proper save/restore of IRQ state | ☐ |

### 9.3 IPC & Protocol

| Check | Description | Status |
|-------|-------------|--------|
| Struct Packing | Shared structs use __attribute__((packed)) | ☐ |
| Endianness | htonl/ntohl for network fields | ☐ |
| No Pointers in IPC | Shared structs contain no pointers | ☐ |
| Queue Overflow | Message queue full case handled | ☐ |
| Protocol Version | Version field checked on receive | ☐ |

### 9.4 Power Management

| Check | Description | Status |
|-------|-------------|--------|
| Suspend Lock-Free | Suspend path doesn't acquire contested locks | ☐ |
| Resume Restore | All HW registers restored on resume | ☐ |
| Wake Source | IRQ wake enabled before suspend | ☐ |
| Power Sequence | Correct power-on/off ordering for peripherals | ☐ |

### 9.5 Timer & Timing

| Check | Description | Status |
|-------|-------------|--------|
| Timer Cleanup | del_timer_sync before free | ☐ |
| Jiffies Wrap | time_after/time_before for comparison | ☐ |
| Clock Source | CLOCK_MONOTONIC for intervals | ☐ |
| Timer Resolution | hrtimer if < 10ms needed | ☐ |

### 9.6 Driver Resources

| Check | Description | Status |
|-------|-------------|--------|
| Probe/Remove Symmetry | Every alloc in probe freed in remove | ☐ |
| devm Consistency | No manual free mixed with devm_* | ☐ |
| copy_from_user Check | Return value verified | ☐ |
| ioctl Errno | Error paths return negative errno | ☐ |

## 10. Application Layer (Userspace)

### 10.1 Process Management

| Check | Description | Status |
|-------|-------------|--------|
| Zombie Reap | waitpid or SIGCHLD handler for every fork | ☐ |
| Daemon Pattern | setsid + double-fork + chdir + fd close | ☐ |
| PID File Lock | flock or O_EXCL for PID file | ☐ |
| FD on exec | O_CLOEXEC set on non-inherited fds | ☐ |
| exec Env Clean | Signal mask reset before exec | ☐ |

### 10.2 POSIX Threads

| Check | Description | Status |
|-------|-------------|--------|
| Cancel Cleanup | pthread_cleanup_push for held resources | ☐ |
| Stack Size | Appropriate for embedded memory constraint | ☐ |
| Cond Wait Loop | while(!cond) not if(!cond) | ☐ |
| Mutex Attribute | Recursive/errorcheck/priority-inherit as needed | ☐ |
| Detached Thread | No reference to caller's stack | ☐ |

### 10.3 Memory (Userspace)

| Check | Description | Status |
|-------|-------------|--------|
| Fragmentation | Memory pool for fixed-size hot-path alloc | ☐ |
| mmap/munmap Pair | Every mmap has matching munmap | ☐ |
| snprintf Bounds | snprintf size checked, return value checked | ☐ |
| No VLA w/ User Input | Variable-length arrays bounded | ☐ |
| Recursion Depth | Recursive functions have depth limit | ☐ |

### 10.4 Signals

| Check | Description | Status |
|-------|-------------|--------|
| Handler Safety | Only async-signal-safe calls in handler | ☐ |
| EINTR Retry | Blocking syscalls retry on EINTR | ☐ |
| Signal + Threads | pthread_sigmask directs signals properly | ☐ |
| Mask Inheritance | Signal mask reset before exec in child | ☐ |

### 10.5 Serial / UART

| Check | Description | Status |
|-------|-------------|--------|
| Raw Mode | cfmakeraw for binary protocols | ☐ |
| Framing Protocol | Length header or delimiter with accum loop | ☐ |
| Flow Control | CRTSCTS or IXON/IXOFF as needed | ☐ |

### 10.6 Watchdog & RT

| Check | Description | Status |
|-------|-------------|--------|
| Feed in Long Ops | Watchdog fed during firmware upgrade etc. | ☐ |
| Magic Close | 'V' written before closing /dev/watchdog | ☐ |
| mlockall | RT process locks pages to prevent page fault | ☐ |
| No malloc in RT | Pre-allocated memory in critical path | ☐ |
| Priority Inherit | PTHREAD_PRIO_INHERIT on shared mutexes | ☐ |

### 10.7 Toolchain & Portability

| Check | Description | Status |
|-------|-------------|--------|
| Cross-Compiler | CC points to target toolchain | ☐ |
| Fixed-Width Types | uint32_t for IPC/protocol, not int/long | ☐ |
| Float ABI Match | All objects same float ABI | ☐ |
| Locale Independent | C locale for data parsing | ☐ |
