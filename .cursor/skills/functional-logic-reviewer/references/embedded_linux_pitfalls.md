# Embedded Linux Pitfalls

Domain-specific bug patterns for embedded Linux systems. Organized by subsystem.

## Table of Contents

**Kernel / Driver Layer:**
1. [Memory & DMA](#1-memory--dma)
2. [Concurrency & Synchronization](#2-concurrency--synchronization)
3. [Interrupt Handling (ISR)](#3-interrupt-handling-isr)
4. [IPC & Protocols](#4-ipc--protocols)
5. [Network Stack](#5-network-stack)
6. [Storage & Filesystem](#6-storage--filesystem)
7. [Timer & Timing](#7-timer--timing)
8. [Power Management](#8-power-management)
9. [Device Driver Patterns](#9-device-driver-patterns)
10. [Init/Shutdown Ordering](#10-initshutdown-ordering)
11. [ARM Architecture Specifics](#11-arm-architecture-specifics)

**Application Layer (Userspace):**
12. [Process & Daemon Management](#12-process--daemon-management)
13. [POSIX Threads (pthread)](#13-posix-threads-pthread)
14. [Userspace Memory Management](#14-userspace-memory-management)
15. [Signal Handling](#15-signal-handling)
16. [Serial / UART Communication](#16-serial--uart-communication)
17. [Userspace Watchdog](#17-userspace-watchdog)
18. [Real-Time Scheduling](#18-real-time-scheduling)
19. [Cross-Compilation & Toolchain](#19-cross-compilation--toolchain)
20. [System Call & Library Pitfalls](#20-system-call--library-pitfalls)
21. [Log & Debug](#21-log--debug)
22. [Resource Release on All Exit Paths](#22-resource-release-on-all-exit-paths)

---

## 1. Memory & DMA

### 1.1 DMA Buffer Alignment

**Pitfall**: DMA buffers not aligned to cache line boundary (typically 32 or 64 bytes on ARM).

**Symptom**: Intermittent data corruption, cache coherency issues.

**Detection**:
- Check `malloc`/`kmalloc` for DMA buffers — must use `dma_alloc_coherent`, `kmalloc(..., GFP_DMA)`, or manually aligned allocation
- Check if `ALIGN()` macro is applied before DMA transfer
- Verify `dma_map_single`/`dma_unmap_single` pairs around DMA operations

**Example Bug**:
```c
// BAD: stack buffer used for DMA — not cache-aligned, may be reclaimed
char buf[256];
dma_transfer(dev, buf, 256);  // UB: stack memory as DMA target

// GOOD:
void *buf = dma_alloc_coherent(dev, 256, &dma_handle, GFP_KERNEL);
```

### 1.2 Cache Coherency Between CPU and DMA

**Pitfall**: CPU cache holds stale data after DMA write, or DMA reads stale data before CPU flush.

**Detection**:
- After DMA-to-memory: verify `dma_sync_single_for_cpu()` before CPU reads
- Before memory-to-DMA: verify `dma_sync_single_for_device()` after CPU writes
- Check for missing `wmb()`/`rmb()` memory barriers around MMIO

### 1.3 Memory-Mapped I/O (MMIO)

**Pitfall**: Using regular pointer dereference for hardware registers instead of `readl()`/`writel()`.

**Why it matters**: Compiler may reorder, cache, or optimize away register accesses.

**Detection**:
- Search for direct pointer dereference of `ioremap()` returned addresses
- Verify all HW register access uses `ioread32`/`iowrite32` or `readl`/`writel`

### 1.4 Slab/Kmalloc Size Classes

**Pitfall**: Allocating slightly over a size class boundary wastes memory; in constrained embedded systems this causes OOM.

**Detection**: Check allocations near power-of-2 boundaries (e.g., 513 bytes → 1024 byte slab).

### 1.5 mmap Page Boundary Issues

**Pitfall**: `mmap` offset or size not page-aligned.

**Detection**: Verify `offset % PAGE_SIZE == 0` and size is rounded up to PAGE_SIZE.

---

## 2. Concurrency & Synchronization

### 2.1 Mutex in Atomic/Interrupt Context

**Pitfall**: Using mutex (which can sleep) inside spinlock-held section, interrupt handler, or softirq.

**Symptom**: Kernel BUG/scheduling-while-atomic panic.

**Detection**:
- Trace call paths from ISR/softirq/tasklet → verify no mutex_lock
- Check spinlock-held regions for any sleeping function (mutex, kmalloc with GFP_KERNEL, copy_from_user, etc.)

### 2.2 Spinlock Held Too Long

**Pitfall**: Spinlock held across I/O operations, memory allocation, or lengthy computation.

**Symptom**: Latency spikes, watchdog timeout on other cores.

**Detection**: Check code between spin_lock/spin_unlock for:
- Any function that may block or sleep
- Loops with unbounded iteration count
- printk (can be slow under log pressure)

### 2.3 Lock Ordering Violation

**Pitfall**: Module A takes lock1 then lock2; Module B takes lock2 then lock1 → deadlock.

**Detection**:
- Build lock acquisition graph across modules
- Look for cycles in the graph
- Pay special attention to callback patterns (module A holds lock, calls into module B which takes its own lock)

### 2.4 RCU Misuse

**Pitfall**: Blocking inside RCU read-side critical section; not calling synchronize_rcu before freeing.

**Detection**:
- Between `rcu_read_lock()` and `rcu_read_unlock()`: no sleeping functions
- After removing from RCU-protected structure: must call `synchronize_rcu()` or `call_rcu()` before `kfree()`

### 2.5 Priority Inversion

**Pitfall**: High-priority task blocked on mutex held by low-priority task that is preempted by medium-priority task.

**Detection**: In RTOS/RT-Linux, check if priority inheritance protocol is enabled for shared mutexes (`PTHREAD_PRIO_INHERIT`).

### 2.6 Signal Safety

**Pitfall**: Signal handler calls non-async-signal-safe functions (malloc, printf, mutex operations).

**Detection**: List all functions called within signal handlers; cross-check against POSIX async-signal-safe list.

---

## 3. Interrupt Handling (ISR)

### 3.1 ISR Duration

**Pitfall**: ISR does too much work (processing, I/O, allocation).

**Best Practice**: ISR should only acknowledge interrupt, capture essential data, and schedule bottom half (tasklet/workqueue).

**Detection**: Check ISR body for:
- Loops
- Memory allocation
- I/O operations (disk, network)
- printk/logging
- Anything beyond register read + flag set + wake

### 3.2 Shared Data Between ISR and Thread

**Pitfall**: Thread reads variable modified by ISR without volatile or proper barriers.

**Detection**:
- Variables written in ISR and read in thread context: must be `volatile` or accessed via `READ_ONCE`/`WRITE_ONCE`
- Or protected by spin_lock_irqsave/spin_unlock_irqrestore

### 3.3 Nested Interrupt Reentrancy

**Pitfall**: ISR interrupted by higher-priority interrupt that accesses same data.

**Detection**: Check if IRQ is disabled during critical section (`local_irq_save`/`local_irq_restore`).

---

## 4. IPC & Protocols

### 4.1 Struct Padding/Packing Mismatch

**Pitfall**: Two processes share struct via shared memory or message queue; one compiled with different packing.

**Detection**:
- Check all IPC structs for `__attribute__((packed))` or `#pragma pack`
- Verify sizeof(struct) matches on both sides
- Check for pointer members in shared structs (invalid across processes!)

### 4.2 Endianness in Network Protocols

**Pitfall**: Multi-byte fields sent without htons/htonl conversion.

**Detection**: For all struct fields > 1 byte sent over network:
- Verify `htonl`/`htons` at send and `ntohl`/`ntohs` at receive
- Check custom protocols for endianness documentation

### 4.3 Message Queue Overflow

**Pitfall**: Producer sends faster than consumer processes; queue full → message lost silently.

**Detection**:
- Check `mq_send`/`msgsnd` return value handling
- Check queue size configuration
- Verify backpressure mechanism exists

### 4.4 Shared Memory Lifetime

**Pitfall**: One process unmaps/destroys shared memory while another still uses it.

**Detection**: Check shm_unlink/munmap ordering; verify reference counting or ownership protocol.

---

## 5. Network Stack

### 5.1 Socket FD Leak

**Pitfall**: `socket()` called but not `close()`d on error path.

**Detection**: For every `socket()` call, trace all return paths and verify `close()` on each.

### 5.2 SIGPIPE on Broken Connection

**Pitfall**: Writing to closed TCP socket generates SIGPIPE → process killed.

**Detection**: Check for `signal(SIGPIPE, SIG_IGN)` or `MSG_NOSIGNAL` flag on `send()`.

### 5.3 Partial send/recv

**Pitfall**: `send()`/`recv()` may transfer fewer bytes than requested.

**Detection**: Verify loop around send/recv that handles partial transfers:
```c
// BAD:
send(fd, buf, len, 0);  // May send less than len

// GOOD:
while (sent < len) {
    n = send(fd, buf + sent, len - sent, 0);
    if (n <= 0) { /* handle error */ break; }
    sent += n;
}
```

### 5.4 Non-blocking EAGAIN/EWOULDBLOCK

**Pitfall**: Non-blocking socket returns EAGAIN but treated as error.

**Detection**: Verify error handling distinguishes EAGAIN/EWOULDBLOCK/EINTR from fatal errors.

### 5.5 select/poll/epoll fd_set Overflow

**Pitfall**: `select()` with fd >= FD_SETSIZE (1024) → buffer overflow.

**Detection**: If using `select()`, verify fd value check or migration to `epoll`.

---

## 6. Storage & Filesystem

### 6.1 Missing fsync

**Pitfall**: Data written to file but not fsynced → power loss loses data.

**Detection**: For critical data writes (config, state), verify `fsync()`/`fdatasync()` is called.

### 6.2 TOCTOU (Time-of-Check-Time-of-Use)

**Pitfall**: Check file existence/permissions, then open → race with other process.

**Detection**: Look for patterns: `stat()` then `open()`, or `access()` then `open()`. Prefer open-and-check.

### 6.3 Flash Wear Leveling Ignorance

**Pitfall**: Frequently writing same flash location without wear leveling → premature wear-out.

**Detection**: Check write frequency to flash-based storage; verify wear-leveling filesystem (JFFS2/UBIFS) or application-level rotation.

### 6.4 Partial Write / Atomic Update

**Pitfall**: Power loss during write leaves file in corrupted state.

**Detection**: For critical files, verify write-to-temp + rename pattern (atomic on most filesystems):
```c
// GOOD: Atomic update
write_to("config.tmp");
fsync(fd);
rename("config.tmp", "config.dat");
```

---

## 7. Timer & Timing

### 7.1 Timer Callback Use-After-Free

**Pitfall**: Structure containing timer is freed, but timer fires later and accesses freed memory.

**Detection**: Before freeing, verify `del_timer_sync()` (kernel) or timer cancellation + guarantee no pending callback.

### 7.2 Jiffies Wrap-Around

**Pitfall**: Comparing jiffies with `>` instead of `time_after()` → failure after ~49 days (32-bit).

**Detection**: Search for direct jiffies comparison; must use `time_after()`/`time_before()` macros.

### 7.3 CLOCK_REALTIME vs CLOCK_MONOTONIC

**Pitfall**: Using CLOCK_REALTIME for intervals → NTP adjustment causes timer drift or expiration anomaly.

**Detection**: For all interval/timeout measurements, verify CLOCK_MONOTONIC is used.

### 7.4 Timer Resolution / Granularity

**Pitfall**: Requesting 1ms timer on system with 10ms tick → unexpected coarse behavior.

**Detection**: Check if high-resolution timers (hrtimer) are needed for <10ms requirements.

---

## 8. Power Management

### 8.1 Suspend with Held Lock

**Pitfall**: Device suspend callback acquires lock that is already held by suspended thread → deadlock.

**Detection**: Check suspend/resume callbacks for lock acquisition; trace if other paths hold same lock.

### 8.2 Device State Not Restored on Resume

**Pitfall**: Hardware registers reset on power cycle but driver doesn't re-initialize on resume.

**Detection**: Compare register writes in probe/init with resume; verify all essential registers are restored.

### 8.3 Wake Source Not Configured

**Pitfall**: Device should wake system but wake IRQ not enabled before suspend.

**Detection**: Check `enable_irq_wake()` / `disable_irq_wake()` in suspend/resume paths.

### 8.4 Peripheral Power Sequencing

**Pitfall**: Turning off power to peripheral while it's still being accessed.

**Detection**: Verify power-off sequence: stop I/O → wait completion → power off. Not: power off → stop I/O.

---

## 9. Device Driver Patterns

### 9.1 Probe/Remove Resource Symmetry

**Pitfall**: Resource allocated in probe() not freed in remove(). Or freed in wrong order.

**Detection**: List all allocations in probe(); verify 1:1 free in remove() in **reverse order**.

### 9.2 ioctl Error Handling

**Pitfall**: ioctl handler returns 0 on error instead of -errno.

**Detection**: Check all ioctl error paths return negative errno values.

### 9.3 copy_from_user / copy_to_user Return Value

**Pitfall**: Ignoring return value — returns number of bytes NOT copied (0 = success).

**Detection**: Verify return value is checked; non-zero = error (-EFAULT).

### 9.4 Platform Device Resource Release

**Pitfall**: Using `devm_*` APIs mixed with manual free → double free.

**Detection**: If using `devm_kzalloc`, `devm_request_irq`, etc., do NOT manually free in remove(). Pick one paradigm.

---

## 10. Init/Shutdown Ordering

### 10.1 Module Init Dependency

**Pitfall**: Module A's init uses Module B's API, but Module B hasn't initialized yet.

**Detection**: Check module init ordering (Makefile link order, `module_init` priority levels).

### 10.2 Shutdown Resource Destruction Order

**Pitfall**: Destroying communication channel before notifying peers → peer crashes or hangs.

**Detection**: Verify shutdown sequence: notify peers → drain queues → close channels → free resources.

### 10.3 Static Initializer Order (C++)

**Pitfall**: Global object initialization order undefined across translation units.

**Detection**: If C++ is used, check for cross-file static initializer dependencies.

---

## 11. ARM Architecture Specifics

### 11.1 Unaligned Access

**Pitfall**: ARM < v7 faults on unaligned 32-bit access; v7+ may silently produce wrong result for multi-word access.

**Detection**: Check struct member access through cast pointers; verify alignment or use `get_unaligned()`.

### 11.2 Memory Barriers

**Pitfall**: ARM has weak memory model; without barriers, stores may be observed out of order by other cores/DMA.

**Detection**: Check multi-core shared data for `dmb`/`dsb`/`isb` (or Linux `mb()`/`wmb()`/`rmb()`).

### 11.3 NEON/VFP Context in Kernel

**Pitfall**: Using floating-point or NEON in kernel/ISR without saving/restoring VFP context.

**Detection**: Check for float/double operations in kernel code; must be wrapped in `kernel_neon_begin()`/`kernel_neon_end()`.

---

# Application Layer (Userspace) Pitfalls

---

## 12. Process & Daemon Management

### 12.1 Zombie Process Leak

**Pitfall**: `fork()` child exits but parent never calls `waitpid()` → zombie accumulates, eventually exhausting PID space.

**Detection**:
- Every `fork()` must have matching `waitpid`/`wait` or `SIGCHLD` handler with `SA_NOCLDWAIT`
- Check if `signal(SIGCHLD, SIG_IGN)` is set (auto-reap on Linux, but not portable)

**Example**:
```c
// BAD: zombie leak
pid_t pid = fork();
if (pid == 0) { exec_child(); exit(0); }
// parent continues without waitpid

// GOOD: install reaper
struct sigaction sa = { .sa_handler = SIG_DFL, .sa_flags = SA_NOCLDWAIT };
sigaction(SIGCHLD, &sa, NULL);
```

### 12.2 Double fork Daemon Pattern Errors

**Pitfall**: Daemon process doesn't properly detach from terminal:
- Missing `setsid()` → still associated with controlling terminal
- Missing second `fork()` → session leader can acquire tty
- Missing `chdir("/")` → holds mount point busy
- Missing fd close → inherited fds leak

**Detection**: For daemon processes, verify the complete sequence:
```c
fork() → exit parent → setsid() → fork() → exit parent →
chdir("/") → umask(0) → close(0,1,2) → redirect to /dev/null
```

### 12.3 PID File Race

**Pitfall**: Two daemon instances race to create PID file → both run simultaneously.

**Detection**: Verify PID file uses `flock()` or `O_EXCL` for atomic creation. Check if stale PID file is handled (process with recorded PID no longer exists).

### 12.4 exec Without Closing Inherited FDs

**Pitfall**: `fork()+exec()` inherits all parent's open fds (sockets, pipes, device files) → resource leak in child, security risk.

**Detection**:
- Check `O_CLOEXEC` flag on `open()`/`socket()` calls
- Or `fcntl(fd, F_SETFD, FD_CLOEXEC)` after open
- Or loop `close()` from 3 to `sysconf(_SC_OPEN_MAX)` before `exec()`

---

## 13. POSIX Threads (pthread)

### 13.1 Thread Cancellation Cleanup

**Pitfall**: Thread cancelled while holding mutex or with allocated memory → leak/deadlock.

**Detection**:
- Check `pthread_cancel` usage → target thread must have cleanup handlers via `pthread_cleanup_push`/`pthread_cleanup_pop`
- Verify cancellation points are appropriate (not in critical sections)

### 13.2 Thread Stack Size on Embedded

**Pitfall**: Default thread stack (typically 8MB) too large for memory-constrained device; or custom stack too small → silent stack overflow.

**Detection**:
- Check `pthread_attr_setstacksize` for appropriate value
- Typical embedded: 64KB-256KB per thread depending on function depth
- Verify no large stack allocations (VLA, `alloca`, large local arrays) in thread functions

### 13.3 Detached Thread Lifetime

**Pitfall**: Detached thread accesses data from creator's scope after creator exits.

**Detection**:
- `pthread_detach` threads must not reference caller's stack variables
- Verify heap-allocated arguments with clear ownership transfer

### 13.4 Thread-Local Storage Destructor Order

**Pitfall**: TLS destructor accesses another TLS variable that was already destroyed.

**Detection**: Check `pthread_key_create` destructor functions for cross-TLS dependencies.

### 13.5 Condition Variable Spurious Wakeup

**Pitfall**: Using `if` instead of `while` to check condition after `pthread_cond_wait`.

**Detection**:
```c
// BAD:
pthread_mutex_lock(&mtx);
if (!ready)                    // if → may proceed on spurious wakeup
    pthread_cond_wait(&cv, &mtx);
process();
pthread_mutex_unlock(&mtx);

// GOOD:
pthread_mutex_lock(&mtx);
while (!ready)                 // while → re-check after wakeup
    pthread_cond_wait(&cv, &mtx);
process();
pthread_mutex_unlock(&mtx);
```

### 13.6 Mutex Attribute Mismatch

**Pitfall**: Using `PTHREAD_MUTEX_DEFAULT` (undefined behavior on re-lock) when recursive locking is needed.

**Detection**: If a thread may re-enter code path that locks same mutex, must use `PTHREAD_MUTEX_RECURSIVE`. Check for `PTHREAD_MUTEX_ERRORCHECK` for debug builds.

---

## 14. Userspace Memory Management

### 14.1 malloc Fragmentation in Long-Running Process

**Pitfall**: Frequent malloc/free of varying sizes → heap fragmentation → eventual allocation failure despite sufficient total free memory.

**Symptom**: Process RSS grows over days/weeks; `malloc` returns NULL despite free memory shown by `free` command.

**Detection**:
- Check for small/variable-size allocations in hot loops
- Look for allocation pattern: alloc A(small) → alloc B(large) → free A → repeat → "Swiss cheese" heap
- Consider memory pool / slab allocator for fixed-size objects

### 14.2 mmap Leak

**Pitfall**: `mmap()` without matching `munmap()` → virtual address space exhaustion (32-bit: 3GB user limit).

**Detection**: Every `mmap` must have matching `munmap` in all paths. Check error paths after `mmap`.

### 14.3 Heap Buffer Overflow in String Operations

**Pitfall**: `strcpy`/`strcat`/`sprintf` without bounds checking.

**Detection**:
- `strcpy` → `strncpy` or `strlcpy`
- `strcat` → `strncat` or `strlcat`
- `sprintf` → `snprintf`
- `gets` → never use (deprecated/removed)
- Check that `snprintf` return value is compared against buffer size

### 14.4 Use-After-Free via Stale Cache/Index

**Pitfall**: Module A caches pointer to object managed by Module B; Module B frees it; Module A dereferences stale pointer.

**Detection**: For cross-module pointer sharing, verify:
- Reference counting or ownership transfer protocol
- Notification mechanism on free (callback, invalidation)

### 14.5 Stack Overflow via Recursion or VLA

**Pitfall**: Recursive function without depth limit, or Variable-Length Array (VLA) with large input → stack overflow → SIGSEGV.

**Detection**:
- Check recursive functions for depth limit
- Check VLA: `char buf[user_input]` — if `user_input` large → overflow
- On embedded, default stack may be smaller; check `ulimit -s`

---

## 15. Signal Handling

### 15.1 Non-Async-Signal-Safe Functions in Handler

**Pitfall**: Signal handler calls `printf`, `malloc`, `mutex_lock` → undefined behavior.

**POSIX async-signal-safe functions** (partial list): `write`, `_exit`, `signal`, `sigaction`, `read`, `open`, `close`, `fork`, `kill`, `getpid`, `sem_post`.

**Detection**: List all function calls within signal handlers; anything not on the safe list is a bug:
```c
// BAD:
void handler(int sig) {
    printf("caught signal %d\n", sig);  // NOT async-signal-safe
    free(global_ptr);                     // NOT async-signal-safe
}

// GOOD:
volatile sig_atomic_t got_signal = 0;
void handler(int sig) {
    got_signal = 1;  // Only set flag, process in main loop
}
```

### 15.2 Signal Mask Inheritance on fork/exec

**Pitfall**: Parent blocks signals before `fork()`; child inherits blocked mask → child never receives expected signals.

**Detection**: Before `exec()` in child, verify signal mask is reset:
```c
sigset_t full;
sigfillset(&full);
sigprocmask(SIG_UNBLOCK, &full, NULL);
```

### 15.3 EINTR Handling

**Pitfall**: Slow syscall (`read`, `write`, `select`, `poll`, `waitpid`, `sleep`) interrupted by signal returns -1 with `errno == EINTR` → treated as fatal error.

**Detection**: For all blocking syscalls, verify EINTR retry loop:
```c
// GOOD:
do {
    n = read(fd, buf, len);
} while (n == -1 && errno == EINTR);
```

### 15.4 Signal and Thread Interaction

**Pitfall**: In multi-threaded process, signal delivered to arbitrary thread; handler accesses thread-specific data.

**Detection**:
- Verify `pthread_sigmask` is used to direct signals to specific thread
- Or use `sigwait()` pattern: dedicated signal-handling thread

---

## 16. Serial / UART Communication

### 16.1 termios Misconfiguration

**Pitfall**: Canonical mode left enabled for binary protocol → kernel buffers until newline (0x0A); or ISTRIP strips 8th bit → data corruption.

**Detection**: For binary serial protocols, verify:
```c
struct termios tty;
tcgetattr(fd, &tty);
cfmakeraw(&tty);           // Disable ALL processing
tty.c_cc[VMIN] = 1;        // Wait for at least 1 byte
tty.c_cc[VTIME] = timeout;  // Inter-byte timeout
tcsetattr(fd, TCSANOW, &tty);
```
Check: `ICANON` off, `ECHO` off, `ISIG` off, `ISTRIP` off, `ICRNL` off, `OPOST` off.

### 16.2 Partial Read on UART

**Pitfall**: `read()` returns fewer bytes than expected because data hasn't arrived yet → partial message parsed as complete.

**Detection**: Verify framing protocol with length header or delimiter, and accumulation loop:
```c
while (received < expected_len) {
    n = read(fd, buf + received, expected_len - received);
    if (n <= 0) { /* handle error/timeout */ break; }
    received += n;
}
```

### 16.3 DTR/RTS Flow Control Not Configured

**Pitfall**: Hardware flow control not enabled → data loss at high baud rates when receiver is slow.

**Detection**: Check `CRTSCTS` flag for hardware flow control, or `IXON`/`IXOFF` for software flow control.

### 16.4 Baud Rate Mismatch with Custom Divisor

**Pitfall**: Non-standard baud rate requires custom divisor via `BOTHER` / `ioctl(TCSETS2)` — using `cfsetspeed` rounds to nearest standard rate.

**Detection**: For non-standard baud (e.g., 460800, 921600, custom), verify `BOTHER` usage or platform-specific API.

---

## 17. Userspace Watchdog

### 17.1 Watchdog Not Fed on Busy Path

**Pitfall**: Application feeds watchdog in main loop, but long-running operation (firmware upgrade, database rebuild) blocks main loop → watchdog reset.

**Detection**: Verify watchdog feeding continues during all long operations (separate thread or interleaved feeding).

### 17.2 /dev/watchdog Close Behavior

**Pitfall**: Closing `/dev/watchdog` without writing 'V' (magic close) → watchdog continues ticking → system resets.

**Detection**: Check close path writes magic character:
```c
write(wdt_fd, "V", 1);  // Magic close — disarms watchdog
close(wdt_fd);
```
Or if intentional (watchdog should always run), document this.

### 17.3 Watchdog Timeout vs Application Recovery Time

**Pitfall**: Watchdog timeout shorter than application's slowest valid operation → spurious resets.

**Detection**: Verify `WDIOC_SETTIMEOUT` value is greater than worst-case legitimate blocking time.

---

## 18. Real-Time Scheduling

### 18.1 RT Thread Starves Non-RT Threads

**Pitfall**: `SCHED_FIFO`/`SCHED_RR` thread with CPU-bound loop → all `SCHED_OTHER` threads (including system daemons) starved → system hangs.

**Detection**:
- RT threads must have bounded execution time per cycle
- Verify `sched_yield()` or blocking point exists in RT loop
- Check `/proc/sys/kernel/sched_rt_runtime_us` (default 950ms/1s — 95% RT cap)

### 18.2 mlockall for Deterministic Latency

**Pitfall**: RT process page-faults on first access → latency spike (ms to hundreds of ms).

**Detection**: Verify RT process calls:
```c
mlockall(MCL_CURRENT | MCL_FUTURE);  // Lock all pages into RAM
```
And pre-faults stack: `memset(stack_buf, 0, sizeof(stack_buf));`

### 18.3 Priority Inversion in Userspace

**Pitfall**: High-priority RT thread blocks on mutex held by low-priority thread.

**Detection**: Check pthread mutex attributes for `PTHREAD_PRIO_INHERIT`:
```c
pthread_mutexattr_t attr;
pthread_mutexattr_init(&attr);
pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_INHERIT);
pthread_mutex_init(&mutex, &attr);
```

### 18.4 Memory Allocation in RT Path

**Pitfall**: `malloc` in RT thread → glibc may call `mmap`/`brk` → non-deterministic latency, potential page fault.

**Detection**: RT critical path should use pre-allocated memory pools, ring buffers, or fixed-size arrays. No `malloc`/`free`/`new`/`delete` in time-critical section.

---

## 19. Cross-Compilation & Toolchain

### 19.1 Host vs Target Binary

**Pitfall**: Build script accidentally uses host compiler instead of cross-compiler → binary runs on build machine but crashes on target.

**Detection**: Verify `CC`/`CXX` variables point to cross toolchain (e.g., `arm-linux-gnueabihf-gcc`). Check `file` output of generated binary matches target architecture.

### 19.2 Library ABI Mismatch

**Pitfall**: Compiled against toolchain's headers (glibc 2.31) but target has older libc (glibc 2.28) → runtime symbol not found.

**Detection**:
- Check `ldd` or `readelf -d` on target for unresolved symbols
- Verify toolchain sysroot matches target rootfs version

### 19.3 Floating-Point ABI Mismatch (ARM)

**Pitfall**: Mixing hard-float (`-mfloat-abi=hard`) and soft-float objects → silent data corruption in function calls (float args passed in wrong registers).

**Detection**: Verify all objects and libraries use same float ABI:
```bash
readelf -A binary | grep "Tag_ABI_VFP_args"
```

### 19.4 sizeof/alignment Differences

**Pitfall**: `sizeof(long)` is 4 on 32-bit ARM but 8 on 64-bit → struct layout differs between host test and target.

**Detection**: Use fixed-width types (`uint32_t`, `int64_t`) for all serialized/shared/IPC structs. Never use `int`/`long` for protocol fields.

### 19.5 Endianness Issues in Data Files

**Pitfall**: Config/data file generated on little-endian host, loaded on big-endian target (or vice versa for some legacy ARM).

**Detection**: Verify binary data files use explicit endianness conversion or text/JSON format.

---

## 20. System Call & Library Pitfalls

### 20.1 errno Overwrite

**Pitfall**: Checking `errno` after a successful call that may have changed it, or after a second syscall that overwrites the first error.

**Detection**:
```c
// BAD:
ret1 = open(path1, O_RDONLY);
ret2 = open(path2, O_RDONLY);  // errno from open(path1) is lost
if (ret1 < 0) perror("path1");  // WRONG: shows path2's errno

// GOOD:
ret1 = open(path1, O_RDONLY);
int saved_errno = errno;       // Save immediately
ret2 = open(path2, O_RDONLY);
```

### 20.2 Time Functions Pitfalls

**Pitfall**: `time()` granularity is 1 second — useless for sub-second measurements. `gettimeofday()` affected by NTP/adjtime. `clock()` measures CPU time not wall time.

**Detection**: For embedded timing:
- Interval/timeout: `clock_gettime(CLOCK_MONOTONIC, ...)`
- Wall clock: `clock_gettime(CLOCK_REALTIME, ...)`
- CPU profiling: `clock_gettime(CLOCK_PROCESS_CPUTIME_ID, ...)`
- Never subtract `struct timespec` nanoseconds directly (may underflow)

### 20.3 popen / system Command Injection

**Pitfall**: Building shell command from user/external input without sanitization → command injection.

**Detection**:
```c
// BAD:
char cmd[256];
snprintf(cmd, sizeof(cmd), "ping -c 1 %s", user_ip);  // user_ip = "8.8.8.8; rm -rf /"
system(cmd);

// GOOD: Use execvp with argument array
```
Verify no `system()`/`popen()` with externally-influenced strings. Prefer `fork()+exec()` with explicit argument list.

### 20.4 dlopen / Shared Library Pitfalls

**Pitfall**: `dlopen` without `RTLD_NOW` → unresolved symbols crash at runtime. Or missing `dlclose` → handle leak.

**Detection**:
- Use `RTLD_NOW` for early detection of missing symbols
- Check `dlerror()` after `dlopen()` and `dlsym()`
- Verify `dlclose()` on error paths

### 20.5 Locale-Dependent String Functions

**Pitfall**: `strtod`, `sscanf("%f")`, `printf("%f")` behavior depends on `LC_NUMERIC` locale — decimal point might be comma instead of dot → parse failure.

**Detection**: For embedded data parsing, use `strtod` with `uselocale(LC_C)` or manual parsing. Verify `setlocale` is not called or is set to "C"/"POSIX".

### 20.6 select/poll Max FD and Timeout

**Pitfall**: `select()` nfds parameter must be `maxfd + 1` (not count of fds). Passing 0 timeout polls; passing NULL blocks forever.

**Detection**: Check `select(maxfd + 1, ...)` — common bug is `select(fd_count, ...)`.

---

## 21. Log & Debug

### 21.1 Syslog Flood

**Pitfall**: Error condition in fast loop logs every iteration → syslog fills disk / overwhelms syslogd → system slowdown.

**Detection**: Rate-limit logging in hot paths:
```c
static time_t last_log = 0;
if (time(NULL) - last_log >= 5) {  // Log at most once per 5 seconds
    syslog(LOG_ERR, "repeated error...");
    last_log = time(NULL);
}
```

### 21.2 Log File Rotation Not Configured

**Pitfall**: Application writes to log file without rotation → flash/disk full → system malfunction.

**Detection**: Verify logrotate config or application-level size check before write. Especially critical on flash-based embedded systems with limited storage.

### 21.3 printf Debug Left in Production

**Pitfall**: `printf`/`fprintf(stderr)` debug output left in release build → performance impact on serial console, potential information leak.

**Detection**: Verify debug prints use conditional compilation (`#ifdef DEBUG`) or log level check. No unconditional `printf` in hot paths.

### 21.4 core dump on Embedded

**Pitfall**: Process crashes but core dump disabled (`ulimit -c 0`) or no space for core file → no debug info.

**Detection**: Verify production builds either:
- Enable core dumps to designated location with rotation
- Or use `prctl(PR_SET_DUMPABLE, 1)` and configure `/proc/sys/kernel/core_pattern`

---

## 22. Resource Release on All Exit Paths

Any function that acquires non-RAII resources must release them on **every** exit path — error, success, and exception alike. Leaks are most common on success paths because reviewers habitually focus on error handling.

### 22.1 Resource Leak on Early Exit (Any Pattern)

**Pitfall**: Function acquires a resource (`fopen`, `open`, `malloc`, `pthread_mutex_lock`, etc.) but one or more early exit points — `return`, `throw`, macro-generated `return`, or `goto` that skips the release site — leave the resource unreleased.

**Symptom**: Resource count grows monotonically. Long-running process eventually hits `EMFILE` (too many open files), `ENOMEM`, or deadlock (mutex never unlocked). May only manifest under sustained, frequent triggering.

**Common C pattern (goto-based centralized release)**:
```c
int upload_file(const char *path)
{
    int ret_code = OK;
    FILE *fp = fopen(path, "rb");  // resource acquired
    CHK_ERR(fp != NULL, ERR_OPEN, "open failed");  // expands to goto cleanup

    // ... do work ...

    if (http_code >= 200 && http_code <= 299) {
        return OK;     // BUG: bypasses cleanup, fp is never fclose'd
    } else {
        ret_code = ERR_HTTP;
    }

cleanup:
    if (fp) { fclose(fp); }  // only reached on error paths
    return ret_code;
}
```

**Fix — set the return value and fall through to the release site**:
```c
    if (http_code >= 200 && http_code <= 299) {
        ret_code = OK;     // set value, then fall through to cleanup
    } else {
        BC_LOG("unexpected http code %ld", http_code);
        ret_code = ERR_HTTP;
    }

cleanup:
    if (fp) { fclose(fp); }
    return ret_code;
```

**Detection**:
1. Identify all non-RAII resources acquired in the function
2. List **every** exit point: `return`, `throw`, `goto`, and macro-generated exits
3. Determine whether each macro expands to `goto` (reaches the release site) or to `return` (skips it)
4. For each exit that is NOT the final statement after the release site, verify all acquired resources are freed before that exit
5. Pay special attention to `return OK` / `return 0` — success early exits are the most overlooked

### 22.2 RAII + Manual Mix: Partial Release on Early Exit

**Pitfall**: C++ code uses RAII (class destructor) for some resources (e.g., `curl` handle, socket), but manages other resources manually (e.g., `FILE *fp`, raw `malloc` buffer). The RAII destructor runs on all exits automatically, creating a **false sense of safety** — but the manually managed resource is only released where explicitly coded.

**Symptom**: No observed crash (RAII resources are always released), but file descriptors or heap memory accumulate silently.

**Example**:
```cpp
int hpc_upload(req_t *req)
{
    hpc_management hpc_mng;  // RAII: releases bchpc on any exit
    FILE *fp = fopen(req->path, "rb");  // manual: NOT managed by hpc_management
    CHK_ERR(fp != NULL, ERR_OPEN, ...);

    // ...

    if (http_code >= 200 && http_code <= 299) {
        return PUSH_SUCCESS; // hpc_mng destructor runs ✓, but fp is leaked ✗
    }
cleanup:
    if (fp) fclose(fp);  // only reached on error
    return ret_code;
}
```

**Detection**:
- When reviewing a function with both RAII objects and manual resource handles, list them separately
- RAII objects: safe on all exits (destructor always runs)
- Manual handles: only safe if explicitly released before every exit or at a centralized release site that all exits reach
- Any exit that bypasses the explicit release site leaks all manual handles acquired above it

### 22.3 CHK_ERR vs CHK_ERR_RET Confusion

**Pitfall**: A codebase may define two similar macros:
- `CHK_ERR(cond, ret, msg)` → `goto cleanup` on failure ✓ (cleanup runs)
- `CHK_ERR_RET(cond, ret, msg)` → direct `return` on failure ✗ (cleanup skipped)

Developers sometimes use `CHK_ERR_RET` after resources are already acquired, unintentionally leaking them.

**Detection**: After identifying all resource acquisition points (`fopen`, `malloc`, etc.), scan downward for any `CHK_ERR_RET` calls that would `return` before the `cleanup:` label, bypassing release.
