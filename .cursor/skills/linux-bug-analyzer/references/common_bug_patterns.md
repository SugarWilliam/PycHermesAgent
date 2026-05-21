# Common Bug Patterns — Linux Userspace C/C++

Categorized bug patterns with detection methods, code examples, and typical root causes for Linux userspace C/C++ applications. Reference this document when forming hypotheses during bug analysis.

## Table of Contents

1. [Memory Errors](#1-memory-errors)
2. [Concurrency Bugs](#2-concurrency-bugs)
3. [Logic Errors](#3-logic-errors)
4. [Resource Leaks](#4-resource-leaks)
5. [State Machine Defects](#5-state-machine-defects)
6. [IPC / Protocol Errors](#6-ipc--protocol-errors)
7. [String / Buffer Handling](#7-string--buffer-handling)
8. [Linux Userspace Specific](#8-linux-userspace-specific)
9. [C++ Specific](#9-c-specific)

---

## 1. Memory Errors

### 1.1 Use-After-Free

**Symptom**: Crash, data corruption, intermittent wrong values, may work under GDB (timing changes)

**Pattern**:
```c
free(ctx);
// ... later or in another thread ...
ctx->state = IDLE;  // BUG: use-after-free
```

**Detection**:
- Check all `free`/`delete` calls — is the pointer used afterwards?
- Is the pointer set to NULL after free?
- Could another thread still hold a reference?
- Search for `free(xxx)` then grep all subsequent uses of `xxx`

**Fix**: Set pointer to NULL after free. Use reference counting for shared objects. Run with AddressSanitizer (`-fsanitize=address`).

### 1.2 Buffer Overflow (Stack)

**Symptom**: `stack smashing detected`, crash in unrelated function, corrupted local variables

**Pattern**:
```c
char buf[64];
sprintf(buf, "prefix_%s_%s", user_str1, user_str2);  // BUG: no bounds check
// Or:
void func(char *input) {
    char local[128];
    strcpy(local, input);  // BUG: input may exceed 128 bytes
}
```

**Detection**: Find `sprintf`, `strcpy`, `strcat`, `gets`, `scanf("%s",...)` — all unbounded. Check `memcpy`/`memmove` length against destination size.

**Fix**: Use `snprintf`, `strncpy` (with NUL terminator), `strlcpy` if available.

### 1.3 Buffer Overflow (Heap)

**Symptom**: `double free or corruption`, crash in malloc/free, data corruption in unrelated data

**Pattern**:
```c
char *buf = malloc(len);
read(fd, buf, len + 1);  // BUG: reads one byte beyond allocation
```

**Detection**: Compare allocation size with actual write size. Check `realloc` usage — old pointer is invalid after realloc.

### 1.4 Off-By-One

**Symptom**: Occasional corruption at boundary, wrong last element

**Pattern**:
```c
for (int i = 0; i <= count; i++)  // BUG: should be < count
    array[i] = 0;
// Or:
buf[strlen(buf)] = '\0';  // Correct, but:
buf[sizeof(buf)] = '\0';  // BUG: off-by-one if buf is exactly full
```

**Detection**: Check all loop boundaries `<=` vs `<`. Check array index vs allocation size.

### 1.5 Uninitialized Variable

**Symptom**: Random values, works on some builds/platforms, fails on others (stack content differs)

**Pattern**:
```c
int result;
if (condition)
    result = compute();
return result;  // BUG: uninitialized when condition is false

// Or in struct:
struct config cfg;
cfg.timeout = 5;
// BUG: cfg.retry_count not set — contains garbage
use_config(&cfg);
```

**Detection**: Trace all paths from declaration to use — does every path assign a value? Check `struct` initialization — are all fields set? Compile with `-Wuninitialized -Wall`.

### 1.6 Double Free

**Symptom**: `double free or corruption`, crash in malloc/free

**Pattern**:
```c
free(ptr);
if (error_cleanup_needed)
    free(ptr);  // BUG: double free

// Or via goto:
free(buf);
if (next_step_fails)
    goto cleanup;
// ...
cleanup:
    free(buf);  // BUG: may already be freed
```

**Detection**: Trace all error/cleanup paths — can `free` be reached twice for the same pointer? Check `goto cleanup` patterns carefully.

### 1.7 sizeof Errors

**Symptom**: Partial copy, data corruption, under-allocation

**Pattern**:
```c
struct msg *p = malloc(sizeof(p));        // BUG: sizeof(pointer), not sizeof(struct)
memcpy(dst, src, sizeof(src));            // BUG: sizeof(pointer) if src is pointer
memset(array, 0, sizeof(array));          // BUG: sizeof(pointer) if array is function parameter
```

**Detection**: Find `sizeof(ptr)` where `sizeof(*ptr)` or `sizeof(struct_type)` was intended. In functions, array parameters decay to pointers.

---

## 2. Concurrency Bugs

### 2.1 Data Race

**Symptom**: Intermittent wrong values, works under GDB (slower execution serializes access), non-deterministic

**Pattern**:
```c
// Thread A                    // Thread B
shared_count++;                shared_count++;  // BUG: no lock, not atomic
```

**Detection**: Find shared global/static variables. Check all access sites — are they protected by the same mutex? Use ThreadSanitizer (`-fsanitize=thread`).

### 2.2 Deadlock (Lock Ordering)

**Symptom**: Hang, all related threads blocked, program stops responding

**Pattern**:
```c
// Thread A:                   // Thread B:
pthread_mutex_lock(&lock_A);   pthread_mutex_lock(&lock_B);
pthread_mutex_lock(&lock_B);   pthread_mutex_lock(&lock_A);  // BUG: opposite order
```

**Detection**: List all lock acquisition sequences across all threads. Find inconsistent ordering. Tool: `valgrind --tool=helgrind`.

### 2.3 Self-Deadlock (Non-Recursive Mutex)

**Symptom**: Single thread hangs on mutex lock

**Pattern**:
```c
pthread_mutex_lock(&mtx);
func_that_also_locks_mtx();  // BUG: same mutex locked again, default mutex is non-recursive
```

**Detection**: Trace call chain from every lock site — can the same lock be reached again?

**Fix**: Use `PTHREAD_MUTEX_RECURSIVE` or restructure to avoid re-entry.

### 2.4 Missing Unlock on Error Path

**Symptom**: Hang after error condition, intermittent deadlock

**Pattern**:
```c
pthread_mutex_lock(&lock);
ret = do_something();
if (ret < 0)
    return ret;       // BUG: lock not released
pthread_mutex_unlock(&lock);
```

**Detection**: For every `pthread_mutex_lock`, trace ALL return/goto/break paths — does every path reach `pthread_mutex_unlock`?

### 2.5 Spurious Wakeup

**Symptom**: Condition variable wakes up but condition not met, race in producer-consumer

**Pattern**:
```c
pthread_mutex_lock(&mtx);
if (!ready)                              // BUG: should be while (!ready)
    pthread_cond_wait(&cond, &mtx);
// May reach here with ready still false
```

**Detection**: Find all `pthread_cond_wait` — is the condition checked with `while` (correct) or `if` (bug)?

### 2.6 Signal Handler Safety

**Symptom**: Random crash, deadlock, corrupted output — only when signal fires during certain operations

**Pattern**:
```c
void handler(int sig) {
    printf("caught signal\n");   // BUG: printf is not async-signal-safe
    free(global_buffer);         // BUG: free is not async-signal-safe
    pthread_mutex_lock(&mtx);   // BUG: may deadlock if signal fires while mtx held
}
```

**Detection**: Check all functions called in signal handlers against POSIX async-signal-safe list. Only `write()`, `_exit()`, `signal()`, and a few others are safe.

**Fix**: In signal handler, only set a `volatile sig_atomic_t` flag; check it in main loop.

---

## 3. Logic Errors

### 3.1 Condition Reversal

**Symptom**: Opposite behavior from expected

**Pattern**:
```c
if (is_valid)
    return -EINVAL;    // BUG: should be !is_valid
```

**Detection**: Compare each condition with the intent described in bug report.

### 3.2 Wrong Operator

**Symptom**: Always true/false condition, wrong calculation

**Pattern**:
```c
if (a = b)           // BUG: assignment instead of comparison (==)
if (flags & FLAG_A && flags & FLAG_B)  // BUG: precedence — & binds tighter than &&
    // Actually parsed as: flags & (FLAG_A && flags) & FLAG_B
```

**Detection**: Check operators in conditions: `=` vs `==`, `&` vs `&&`, `|` vs `||`. Check operator precedence with bitwise ops.

**Fix**: Use explicit parentheses: `(flags & FLAG_A) && (flags & FLAG_B)`.

### 3.3 Missing Break in Switch

**Symptom**: Falls through to next case, executes multiple handlers

**Pattern**:
```c
switch (cmd) {
    case CMD_START:
        handle_start();
        // BUG: falls through to CMD_STOP
    case CMD_STOP:
        handle_stop();
        break;
}
```

**Detection**: Check every `case` in `switch` for `break`/`return`/`goto`.

### 3.4 Integer Overflow / Underflow

**Symptom**: Huge allocation, wrap-around, negative size interpreted as large positive

**Pattern**:
```c
size_t alloc_size = count * elem_size;   // BUG: overflow if count is large
unsigned remaining = total - used;       // BUG: underflow if used > total
int16_t sum = a + b;                     // BUG: overflow if a+b > 32767
```

**Detection**: Check arithmetic near boundaries. Check signed/unsigned conversions. Check multiplication used for allocation size.

### 3.5 Macro Side Effects

**Symptom**: Expression evaluated twice, unexpected increment

**Pattern**:
```c
#define MAX(a, b) ((a) > (b) ? (a) : (b))
int result = MAX(x++, y);  // BUG: x may be incremented twice
```

**Detection**: Find macro invocations with side-effect expressions (`++`, `--`, function calls).

---

## 4. Resource Leaks

### 4.1 File Descriptor Leak

**Symptom**: `EMFILE` ("too many open files"), `open()` fails, eventual system resource exhaustion

**Pattern**:
```c
int fd = open(path, O_RDONLY);
if (process(fd) < 0)
    return -1;        // BUG: fd not closed on error
close(fd);
```

**Detection**: For every `open`/`socket`/`accept`/`dup`/`epoll_create`/`timerfd_create`/`eventfd`, trace ALL return paths — does every path reach `close`?

### 4.2 Memory Leak

**Symptom**: Gradual RSS growth, OOM after long running

**Pattern**:
```c
char *buf = malloc(size);
if (parse(buf) < 0)
    return -1;        // BUG: buf not freed
free(buf);
```

**Detection**: For every `malloc`/`calloc`/`realloc`/`strdup`/`asprintf`, trace all paths to verify `free`. Run with Valgrind (`valgrind --leak-check=full`).

### 4.3 Leaked on Realloc Failure

**Symptom**: Memory leak when system is under memory pressure

**Pattern**:
```c
buf = realloc(buf, new_size);  // BUG: if realloc fails, returns NULL
                                // Original buf is leaked and pointer lost
```

**Fix**: `tmp = realloc(buf, new_size); if (tmp) buf = tmp; else handle_error();`

### 4.4 Thread / Timer Leak

**Symptom**: Growing thread count, accumulating timers, resource exhaustion

**Detection**: For every `pthread_create`, find matching `pthread_join` or `pthread_detach`. For every `timer_create`/`timerfd_create`, find matching delete/close.

---

## 5. State Machine Defects

### 5.1 Missing State Transition

**Symptom**: Gets stuck in a state, feature does not work in specific scenario

**Detection**: List all designed states and transitions. Compare against code switch/if-else. Missing transition = bug.

### 5.2 Invalid State Transition

**Symptom**: Unexpected behavior, protocol violation, corruption

**Detection**: Check if code allows transitions that should be forbidden. Look for missing state validation before action.

### 5.3 State Not Reset on Re-entry

**Symptom**: Works first time, fails on retry or re-open

**Pattern**:
```c
static int state = STATE_IDLE;
void start() {
    if (state != STATE_IDLE)
        return;  // BUG: if previous session ended abnormally, state is not IDLE
    state = STATE_RUNNING;
}
```

**Detection**: Check if state variables are properly reset on error/cleanup/restart paths.

---

## 6. IPC / Protocol Errors

### 6.1 Struct Size Mismatch

**Symptom**: Garbled fields in received message, wrong values, partial read

**Pattern**:
```c
// Process A: compiled with gcc default alignment — sizeof(msg_t) = 32
// Process B: compiled with #pragma pack(1) — sizeof(msg_t) = 28
send(fd, &msg, sizeof(msg_t), 0);  // BUG: receiver reads wrong field offsets
```

**Detection**: Check struct definitions on both ends. Verify `#pragma pack` and `__attribute__((packed))` consistency. Check `sizeof` match.

### 6.2 Partial Send/Recv

**Symptom**: Truncated message, garbled subsequent messages

**Pattern**:
```c
ret = send(fd, buf, len, 0);  // BUG: ret may be < len (partial send)
// Must loop until all bytes sent
ret = recv(fd, buf, len, 0);  // BUG: ret may be < len (partial recv)
// Must handle message framing
```

**Detection**: Check all `send`/`recv`/`write`/`read` — is return value checked and looped?

### 6.3 Endianness Error

**Symptom**: Works locally, garbled on cross-arch (ARM ↔ x86)

**Detection**: Find multi-byte fields in network/IPC protocol. Check for `htons`/`htonl`/`ntohs`/`ntohl`.

### 6.4 EINTR Not Retried

**Symptom**: Intermittent failure, syscall returns -1 when signal arrives

**Pattern**:
```c
ret = read(fd, buf, len);
if (ret < 0)
    return -1;  // BUG: should retry if errno == EINTR
```

**Detection**: Check all blocking syscalls (`read`, `write`, `select`, `poll`, `accept`, `connect`, `waitpid`) for EINTR handling.

---

## 7. String / Buffer Handling

### 7.1 Missing NUL Terminator

**Symptom**: Garbage after string content, `strlen()` reads past buffer

**Pattern**:
```c
char buf[8];
strncpy(buf, src, sizeof(buf));  // BUG: if strlen(src) >= 8, no NUL terminator
printf("%s", buf);                // Reads past buf
```

**Fix**: Always `buf[sizeof(buf)-1] = '\0';` after `strncpy`.

### 7.2 Format String Mismatch

**Symptom**: Wrong output, crash, undefined behavior

**Pattern**:
```c
printf("%d", (unsigned long)val);      // BUG: %d for unsigned long — use %lu
printf("%s", integer_value);           // BUG: prints garbage or crashes
printf("%d %d", a);                    // BUG: too few arguments
snprintf(buf, sizeof(buf), user_str);  // BUG: user_str used as format — injection
```

**Detection**: Compare every format specifier with its argument type. Compile with `-Wformat`.

### 7.3 Locale-Dependent Parsing

**Symptom**: Works in some regions, fails in others (decimal point: `.` vs `,`)

**Detection**: Check `strtod`, `sscanf("%f")`, `atof` — these are locale-dependent. Use `strtod` with explicit `LC_NUMERIC=C` or manual parsing.

---

## 8. Linux Userspace Specific

### 8.1 Process Management

**Zombie leak**: `fork()` without `waitpid()` or `SIGCHLD` handler — child becomes zombie.

**FD inheritance**: `open()`/`socket()` without `O_CLOEXEC`/`SOCK_CLOEXEC` — child inherit fds on `exec()`.

**PID file race**: Check-then-write PID file without file lock — two instances may start.

**Signal mask inheritance**: `fork()` inherits blocked signals — child may miss signals.

### 8.2 epoll / select / poll

**`select()` FD_SETSIZE**: `select()` with fd >= 1024 overflows `fd_set` buffer. Use `poll()` or `epoll`.

**epoll stale fd**: After `close(fd)`, epoll automatically removes it. But if fd number is reused (new open), stale epoll interest may fire for wrong connection.

**Level vs Edge trigger**: `EPOLLET` requires draining all data in one callback. `EAGAIN` finish detection missing = data stuck.

### 8.3 Daemon Patterns

**Double fork**: Missing second `fork()` — process keeps controlling terminal.

**Working directory**: Missing `chdir("/")` — holds mount point, prevents unmount.

**File creation mask**: Missing `umask(0)` — files created with unexpected permissions.

**Standard fd**: Missing redirect of stdin/stdout/stderr to `/dev/null` — writes crash or hang on closed fd.

### 8.4 Shared Memory / mmap

**Unmap leak**: `mmap()` without matching `munmap()` — virtual address space exhaustion.

**Truncation**: `shm_open` + `mmap` without `ftruncate` — SIGBUS on access beyond file size.

**Synchronization**: Multiple processes accessing shared memory without `pthread_mutex` (with `PTHREAD_PROCESS_SHARED`) or `sem_t`.

### 8.5 Timer and Timeout

**CLOCK_REALTIME jump**: Using `CLOCK_REALTIME` for timeout — NTP adjustment or manual clock change causes premature/delayed timeout. Use `CLOCK_MONOTONIC`.

**timerfd not drained**: `timerfd_create` in edge-triggered epoll — must `read()` the expiration count, else no further notifications.

**Watchdog feed**: Long blocking operation without watchdog feed — system resets.

---

## 9. C++ Specific

### 9.1 Object Lifetime

**Dangling reference**: Returning reference to local variable or temporary.

```cpp
const std::string& getName() {
    std::string name = buildName();
    return name;  // BUG: returns reference to local — destroyed on return
}
```

**Iterator invalidation**: Modifying container while iterating.

```cpp
for (auto it = vec.begin(); it != vec.end(); ++it) {
    if (should_remove(*it))
        vec.erase(it);  // BUG: invalidates it — undefined behavior
}
```

### 9.2 RAII Violations

**Missing virtual destructor**: Base class pointer, derived class deleted — derived destructor not called.

```cpp
class Base { ~Base() {} };           // BUG: not virtual
class Derived : public Base { ~Derived() { cleanup(); } };
Base *p = new Derived();
delete p;  // Derived::~Derived() not called — resource leak
```

**Exception in constructor**: Resources allocated before exception — no destructor called.

### 9.3 Smart Pointer Misuse

**Circular reference**: `shared_ptr` cycle — memory never freed.

```cpp
struct Node {
    std::shared_ptr<Node> next;  // BUG if circular — use weak_ptr for back-references
};
```

**Shared from raw**: Creating multiple `shared_ptr` from same raw pointer — double delete.

```cpp
auto p1 = std::shared_ptr<Obj>(raw_ptr);
auto p2 = std::shared_ptr<Obj>(raw_ptr);  // BUG: double delete
```

### 9.4 Move Semantics Errors

**Use-after-move**: Accessing object after `std::move`.

```cpp
std::string s = "hello";
std::string t = std::move(s);
printf("%s", s.c_str());  // BUG: s is in moved-from state
```

---

## 10. C Language Traps (Undefined / Implementation-Defined Behavior)

Patterns that are legal C syntax but produce undefined or implementation-defined behavior — the compiler may "optimize away" the bug, or it may crash on a different platform/optimization level.

### 10.1 Sequence Point Violations

**Symptom**: Different results on different compilers or `-O` levels.

**Pattern**:
```c
a[i] = i++;                    // UB: i read and modified without sequence point
x = f() + g();                 // Unspecified: f() or g() called first
printf("%d %d", i++, i++);     // UB: two modifications without sequence point
```

**Detection**: Find expressions with multiple `++`/`--` on the same variable, or function calls with side effects where order matters. Compile with `-Wall -Wsequence-point`.

### 10.2 Strict Aliasing Violations

**Symptom**: Works at `-O0`, breaks at `-O2`/`-O3`. Optimizer assumes pointers of different types don't alias.

**Pattern**:
```c
float f = 3.14f;
int bits = *(int *)&f;          // BUG: strict aliasing violation — UB

// Correct alternatives:
int bits;
memcpy(&bits, &f, sizeof(bits));   // OK: memcpy is always safe
// Or use union (well-defined in C, not C++):
union { float f; int i; } u = { .f = 3.14f };
int bits = u.i;
```

**Detection**: Find pointer casts between unrelated types (not `void*` or `char*`). Compile with `-fno-strict-aliasing` to test, or `-Wstrict-aliasing`.

### 10.3 Signed/Unsigned Comparison Trap

**Symptom**: Condition always true or always false. Negative value becomes huge positive.

**Pattern**:
```c
int len = -1;
if (len < sizeof(buf))         // BUG: len promoted to unsigned — becomes 0xFFFFFFFF
    // Always false on 32-bit — sizeof returns size_t (unsigned)

unsigned u = 10;
int s = -1;
if (s > u)                     // BUG: s promoted to unsigned — true! (-1 > 10)
    printf("unexpected!\n");
```

**Detection**: Compare types on both sides of `<`, `>`, `<=`, `>=`, `==`. If one is signed and other is unsigned, the signed is implicitly converted. Compile with `-Wsign-compare`.

### 10.4 Integer Promotion Trap

**Symptom**: Arithmetic on small types (uint8_t, int16_t) produces unexpected results.

**Pattern**:
```c
uint8_t a = 200, b = 100;
uint8_t sum = a + b;           // sum = 44 (300 wraps to 44) — but:
if (a + b > 255)               // TRUE! a+b promoted to int = 300
    // This branch IS taken
// The promotion to int happens before the comparison

uint16_t x = 0xFFFF;
uint16_t y = ~x;               // BUG on 32-bit: ~x promotes to int, result = 0xFFFF0000, not 0x0000
```

**Detection**: Find arithmetic on `uint8_t`/`int8_t`/`uint16_t`/`int16_t` — C promotes to `int` before arithmetic. The result may not fit back in the small type.

### 10.5 Variadic Function Argument Promotion

**Symptom**: Wrong values printed, crash in `printf`-like functions.

**Pattern**:
```c
float f = 3.14f;
printf("%f", f);               // OK: float promoted to double, %f expects double

uint8_t val = 42;
printf("%d", val);             // OK: promoted to int

// But:
long long ll = 123456789LL;
printf("%d", ll);              // BUG: %d reads 4 bytes, ll is 8 bytes — stack misread
printf("%lld", ll);            // Correct

size_t sz = 1024;
printf("%d", sz);              // BUG: size_t may be 64-bit — use %zu
```

**Detection**: Verify every `printf`/`syslog`/`snprintf` format specifier matches the argument type. Use `-Wformat`.

### 10.6 Bitfield Portability

**Symptom**: Works on one compiler/platform, wrong field values on another.

**Pattern**:
```c
struct flags {
    unsigned int a : 3;
    unsigned int b : 5;
    // Implementation-defined:
    //   - Bit ordering (MSB-first vs LSB-first) — varies by platform
    //   - Whether int bitfield is signed or unsigned — varies by compiler
    //   - Padding between bitfields — varies by ABI
};
// NEVER use bitfields in protocol/IPC structs — use explicit bitmasks instead
```

**Detection**: Find `struct` with bitfields used in `send`/`recv`/`write`/`read`/`memcpy` between processes or between host and device. Replace with explicit shift/mask operations.

### 10.7 Flexible Array Member sizeof

**Symptom**: Under-allocation, buffer overflow when writing to flexible array.

**Pattern**:
```c
struct msg {
    int type;
    int len;
    char data[];               // Flexible array member (C99)
};
struct msg *m = malloc(sizeof(struct msg));  // BUG: sizeof doesn't include data[]
// Correct:
struct msg *m = malloc(sizeof(struct msg) + data_len);
```

**Detection**: Find `struct` with `[]` or `[0]` trailing member. Check allocation size includes the dynamic part.

### 10.8 Comma Operator Confusion

**Symptom**: Fewer arguments than expected, wrong value used.

**Pattern**:
```c
func(a, (b, c));              // Passes 2 args, not 3. (b, c) evaluates b then returns c.
int x = (flag = 1, value);    // x = value, not flag — comma operator returns right operand

// Common in macros:
#define INIT(a, b)  do { x = a; y = b; } while(0)
INIT(1, 2);                   // OK
if (cond) INIT(1, 2);         // OK with do-while
```

**Detection**: Find comma inside function calls or assignments where it might be confused with argument separator.

### 10.9 Dangling Pointer from Stack Array

**Symptom**: Returned pointer works briefly then causes corruption or crash.

**Pattern**:
```c
char *get_name() {
    char buf[64];
    snprintf(buf, sizeof(buf), "device_%d", id);
    return buf;                // BUG: buf is on stack — dangling pointer after return
}

int *get_array() {
    int arr[] = {1, 2, 3};
    return arr;                // BUG: same problem
}
```

**Detection**: Find `return` of address of local variable (array, struct, or `&local`). Compile with `-Wreturn-local-addr`.

### 10.10 volatile Misunderstanding

**Symptom**: Works with `-O0`, thread communication breaks with `-O2`. Or: deemed "atomic" but isn't.

**Pattern**:
```c
volatile int flag = 0;         // Does NOT guarantee:
                                //   - Atomicity of read-modify-write (flag++)
                                //   - Memory ordering between threads
                                //   - Visibility to other CPUs (no memory barrier)

// volatile is ONLY appropriate for:
//   - Signal handler communication (volatile sig_atomic_t)
//   - Memory-mapped hardware registers
//   - longjmp/setjmp variables

// For thread synchronization, use:
//   - pthread_mutex / pthread_cond
//   - C11 _Atomic / stdatomic.h
//   - GCC __atomic builtins
```

**Detection**: Find `volatile` used for inter-thread communication. It's almost always wrong — should be `_Atomic` or protected by mutex.

---

## 11. Embedded Linux System Patterns

Patterns specific to embedded Linux devices (IPC cameras, IoT, network appliances) that don't appear in typical server/desktop development.

### 11.1 Flash / eMMC Write Patterns

**Data loss on power failure**:
```c
fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
write(fd, data, len);
close(fd);                     // BUG: data may be in page cache — lost on power cut
// Fix: fsync(fd) before close, or use O_SYNC (slower)
```

**Flash wear**: Frequent small writes to same file wear out flash sectors. Use write coalescing or ramfs + periodic sync.

**Filesystem corruption**: Writing to mounted filesystem during improper shutdown. Use read-only rootfs + overlay, or journaling filesystem.

**Atomic file update** pattern:
```c
// Write to temp file, fsync, rename (atomic on most filesystems):
fd = open(path_tmp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
write(fd, data, len);
fsync(fd);
close(fd);
rename(path_tmp, path);        // Atomic replace on same filesystem
fsync(open(dir, O_RDONLY));    // Sync directory entry (optional, for extra safety)
```

### 11.2 Watchdog Patterns

**Long operation starvation**: Operations like firmware upgrade, factory reset, or large file transfer may take longer than watchdog timeout.

**Detection**: Find long blocking operations (`sleep`, `select` with long timeout, large file I/O, network transfer) and check if watchdog is fed during or around them.

**Fix**: Feed watchdog in progress callbacks, or temporarily extend watchdog timeout during known long operations.

**Watchdog not started**: Device runs without hardware watchdog — hangs are not recovered.

**Watchdog inherited by child**: After `fork()`, child process may inherit watchdog fd and interfere with feeding.

### 11.3 Boot Order / Init Race

**Symptom**: Feature fails on cold boot but works after manual restart of the service.

**Pattern**: Service A depends on service B (e.g., network service depends on driver module loaded), but init system starts them in parallel or wrong order.

**Detection**:
- Check init scripts / systemd unit files for dependency declarations
- Look for retry-on-failure patterns that mask init order bugs
- Check if service accesses devices/sockets that might not exist yet at boot time

**Fix**: Explicit dependency in init system, or readiness-check loop with timeout before proceeding.

### 11.4 Resource Limits

**ulimit hits**:
- `RLIMIT_NOFILE` (default 1024) — hit when many connections/files open
- `RLIMIT_NPROC` — hit when spawning many threads (`pthread_create` fails with `EAGAIN`)
- `RLIMIT_STACK` — stack overflow for threads with small stack
- `RLIMIT_CORE` — core dump not generated if set to 0

**OOM Killer**: Linux overcommits memory by default. When physical memory is exhausted, OOM killer picks a process to kill. Embedded devices with limited RAM hit this often.

**Detection**: Check `dmesg` for `oom-killer` messages. Check `/proc/<pid>/oom_score`. Set `oom_score_adj` for critical processes.

**tmpfs full**: `/tmp`, `/dev/shm`, `/run` are often tmpfs on embedded — writing large files fills RAM.

### 11.5 Thread Stack Size

**Default 8MB**: `pthread_create` default stack is 8MB (varies by platform). For embedded with 64-128MB RAM and many threads, this can exhaust virtual address space.

**Too small**: Setting stack too small via `pthread_attr_setstacksize` causes stack overflow — silent corruption or SIGSEGV.

**Detection**: Check total thread count × stack size against available RAM. Use `pthread_attr_getstacksize` to verify. Check for deep recursion or large local arrays in thread functions.

### 11.6 Heap Fragmentation

**Symptom**: `malloc` returns NULL despite `free()` having returned sufficient memory. Common after long runtime with many small alloc/free cycles.

**Detection**: Monitor `/proc/<pid>/status` for `VmRSS` growth over time. Use `malloc_info()` or `mallopt()` to check arena state.

**Mitigation**: Use memory pools for fixed-size objects. Use `malloc_trim()` periodically. Preallocate buffers at startup.

### 11.7 Time / RTC Patterns

**RTC not set**: Device boots with epoch time (1970-01-01). Time-based logic (certificate validation, log rotation, event scheduling) fails.

**NTP jump**: After NTP sync, `CLOCK_REALTIME` jumps forward/backward. Timers based on `CLOCK_REALTIME` fire immediately or very late.

**Fix**: Use `CLOCK_MONOTONIC` for intervals and timeouts. Use `CLOCK_REALTIME` only for human-readable timestamps. Handle NTP jump gracefully.

### 11.8 TOCTOU File Race

**Symptom**: Intermittent permission bypass, wrong file operated on.

**Pattern**:
```c
if (access(path, R_OK) == 0) {    // Check
    fd = open(path, O_RDONLY);      // Use — file may have changed between check and use
}
// Or:
if (stat(path, &st) == 0 && S_ISREG(st.st_mode)) {
    fd = open(path, O_RDONLY);      // File may have been replaced with symlink
}
```

**Fix**: Open first, then `fstat` on the fd. Use `O_NOFOLLOW` to prevent symlink attacks. Use `openat()` for directory-relative operations.

---

## 12. Network Socket Patterns

Common bugs in network programming that appear frequently in embedded Linux devices with TCP/UDP connections.

### 12.1 Blocking Connect Without Timeout

**Symptom**: Process hangs for minutes when peer is unreachable.

**Pattern**:
```c
int fd = socket(AF_INET, SOCK_STREAM, 0);
connect(fd, &addr, sizeof(addr));  // Blocks for ~2 minutes (TCP SYN retries) if peer down
```

**Fix**: Set socket to non-blocking, use `connect` + `select`/`poll` with timeout, then check `SO_ERROR` via `getsockopt`.

### 12.2 Missing SO_REUSEADDR

**Symptom**: `bind()` fails with `EADDRINUSE` after server restart.

**Pattern**:
```c
int fd = socket(AF_INET, SOCK_STREAM, 0);
bind(fd, &addr, sizeof(addr));     // Fails if previous instance's socket is in TIME_WAIT
```

**Fix**: Set `SO_REUSEADDR` before `bind()`.

### 12.3 Dead Connection Detection

**Symptom**: Server holds resources for connections where peer silently disappeared (cable unplug, peer crash, network partition).

**Detection**: Check if TCP `SO_KEEPALIVE` is enabled and configured (idle time, interval, probes). Default keepalive is 2 hours — too slow for most applications.

**Fix**: Application-level heartbeat, or configure TCP keepalive: `TCP_KEEPIDLE` (seconds before first probe), `TCP_KEEPINTVL` (seconds between probes), `TCP_KEEPCNT` (failed probes before drop).

### 12.4 TCP Stream Framing

**Symptom**: Garbled messages, messages merged or split.

**Pattern**:
```c
// Sender:
send(fd, &msg, sizeof(msg), 0);
// Receiver:
recv(fd, &msg, sizeof(msg), 0);    // BUG: recv may return partial message or multiple messages
```

TCP is a byte stream, not a message stream. `recv` may return 1 byte or multiple messages in one call.

**Fix**: Use length-prefix framing (send length header first, then payload). Or use fixed-size messages. Always loop on `recv` until complete message received.

### 12.5 DNS Blocking in Event Loop

**Symptom**: Event loop freezes for seconds during DNS resolution.

**Pattern**:
```c
// In event loop or single-threaded server:
struct hostent *h = gethostbyname(hostname);   // Blocks for DNS lookup — may take seconds
// Or:
getaddrinfo(hostname, port, &hints, &res);     // Also blocks
```

**Fix**: Use `getaddrinfo_a()` for async DNS, or do DNS resolution in a separate thread, or use a non-blocking DNS library.

### 12.6 Non-Blocking Socket EAGAIN

**Symptom**: Application spins at 100% CPU, or silently drops data.

**Pattern**:
```c
fcntl(fd, F_SETFL, O_NONBLOCK);
ret = read(fd, buf, len);
if (ret < 0)
    return -1;                 // BUG: EAGAIN/EWOULDBLOCK is not an error — just means "try later"
```

**Detection**: Find non-blocking socket operations and check if `EAGAIN`/`EWOULDBLOCK` is handled separately from real errors.

### 12.7 Multicast / Broadcast Pitfalls

**Missing SO_BROADCAST**: `sendto` with broadcast address fails with `EACCES` unless `SO_BROADCAST` is set.

**Multicast TTL**: Default TTL=1 — multicast doesn't cross routers. Set `IP_MULTICAST_TTL` if needed.

**Interface binding**: `IP_ADD_MEMBERSHIP` with `INADDR_ANY` uses default interface — may be wrong on multi-NIC device. Specify interface explicitly.
