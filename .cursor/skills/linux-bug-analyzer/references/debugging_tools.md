# Debugging Tools Reference

Reference material for adding instrumentation and using debuggers during bug analysis.

## Table of Contents

1. [Strategic Print Placement](#strategic-print-placement)
2. [Print Macros](#print-macros)
3. [Binary Bisection Strategy](#binary-bisection-strategy)
4. [GDB Quick Commands](#gdb-quick-commands)

---

## Strategic Print Placement

When logs are insufficient, add targeted prints at these locations:

- **Function entry/exit** with key parameter values and return value
- **Before and after** suspected faulty operation (especially syscalls)
- **Branch points** to confirm which path is taken
- **Variable values** at each transformation step — especially pointer values, array indices, sizes
- **Error return paths** with `errno` (`strerror(errno)`) or custom error code
- **Lock acquire/release** to detect deadlock ordering
- **Memory alloc/free** with pointer address to detect double-free and use-after-free

---

## Print Macros

```c
// Basic debug print — includes file, line, function for easy grep
#define DBG(fmt, ...) \
    fprintf(stderr, "[DBG] %s:%d %s: " fmt "\n", \
        __FILE__, __LINE__, __func__, ##__VA_ARGS__)

// Print with errno — use immediately after failed syscall
#define DBG_ERR(fmt, ...) \
    fprintf(stderr, "[ERR] %s:%d %s: " fmt " (errno=%d: %s)\n", \
        __FILE__, __LINE__, __func__, ##__VA_ARGS__, errno, strerror(errno))

// Print pointer for memory tracking
#define DBG_PTR(tag, ptr) \
    fprintf(stderr, "[MEM] %s:%d %s: %s=%p\n", \
        __FILE__, __LINE__, __func__, tag, (void*)(ptr))

// Usage examples
DBG("state=%d, buf_len=%zu, ptr=%p", state, buf_len, (void*)ptr);
DBG_ERR("open(%s) failed", path);
DBG_PTR("alloc ctx", ctx);
DBG_PTR("free ctx", ctx);
```

---

## Binary Bisection Strategy

When the bug region is large, use binary bisection to narrow quickly:

1. Place a print at the **midpoint** of the suspected region
2. Run and observe — did the midpoint print execute with correct values?
3. If yes: bug is **after** the midpoint → repeat in second half
4. If no / wrong values: bug is **before or at** the midpoint → repeat in first half
5. Iterate until the region is 5-10 lines — then read code carefully

---

## GDB Quick Commands

### Core Dump Analysis

```bash
gdb <program> <core-file>
(gdb) bt full            # full backtrace with local variables
(gdb) frame N            # switch to frame N
(gdb) info locals        # show all local variables
(gdb) print *ptr         # dereference pointer
(gdb) info threads       # list all threads (deadlock diagnosis)
(gdb) thread apply all bt # backtrace for all threads
```

### Live Debugging

```bash
gdb --args <program> <args>
(gdb) break func_name    # set breakpoint
(gdb) watch variable     # break when variable changes
(gdb) catch signal SIGSEGV  # break on signal
```
