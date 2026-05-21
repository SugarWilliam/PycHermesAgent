# Naming Conventions & Spelling Rules

Detailed naming convention reference for Linux-style C code review. Applies to all new or renamed identifiers.

## Table of Contents
1. [Linux Kernel Naming Style](#1-linux-kernel-naming-style)
2. [Spelling Verification](#2-spelling-verification)
3. [Standard Abbreviations](#3-standard-abbreviations)
4. [Common Misspelling List](#4-common-misspelling-list)
5. [Anti-Patterns](#5-anti-patterns)

---

## 1. Linux Kernel Naming Style

### 1.1 Functions and Variables

**Rule**: `snake_case`, all lowercase, descriptive.

```c
// GOOD:
int get_frame_count(struct stream_ctx *ctx);
static void flush_pending_buffers(struct buf_mgr *mgr);
int retry_count = 0;
char *dev_name = NULL;

// BAD:
int GetFrameCount();          // CamelCase
int getframecount();          // no separation
void flush_PendingBuffers();  // mixed case
int nRetryCount;              // Hungarian notation
```

**Scope-based length guideline**:
- Loop index / tiny scope: short names OK (`i`, `n`, `ret`, `err`)
- Function-scope local: medium names (`buf_len`, `frame_idx`)
- Module-scope / struct fields: descriptive names (`pending_frame_count`, `audio_sample_rate`)
- Global / exported: fully qualified names (`netserver_get_conn_count()`)

### 1.2 Types

**Rule**: Prefer bare `struct`/`enum`/`union` tags. Use `_t` suffix typedef only for truly opaque types.

```c
// GOOD:
struct msg_header {
    uint32_t msg_id;
    uint16_t payload_len;
};
enum stream_state {
    STREAM_STATE_IDLE,
    STREAM_STATE_RUNNING,
    STREAM_STATE_ERROR,
};

// Opaque type — _t suffix acceptable:
typedef struct audio_handle_s audio_handle_t;

// BAD:
typedef struct {              // anonymous struct with typedef
    int x;
} MyStruct;                   // CamelCase typedef
typedef int BOOL;             // Windows-style
```

### 1.3 Macros and Constants

**Rule**: `UPPER_SNAKE_CASE`.

```c
// GOOD:
#define MAX_RETRY_COUNT     5
#define BUF_ALIGN           64
#define STREAM_FLAG_ACTIVE  (1 << 0)

// BAD:
#define maxRetryCount  5      // camelCase
#define Max_Retry      5      // mixed case
```

**Enum constants**: Prefix with type name in UPPER_SNAKE_CASE:

```c
enum log_level {
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
};
```

### 1.4 Struct and Enum Tags

**Rule**: `snake_case`, descriptive noun.

```c
struct frame_buffer { ... };
enum conn_state { ... };
union param_value { ... };
```

### 1.5 Boolean Naming

**Rule**: Prefix with `is_`, `has_`, `can_`, `should_`, `need_`.

```c
// GOOD:
bool is_running;
bool has_audio;
bool can_retry;
bool should_flush;
bool need_restart;

// BAD:
bool running;          // ambiguous — could be a verb
bool audio_enabled;    // acceptable but less consistent
bool flag;             // meaningless name
```

### 1.6 Callbacks and Function Pointers

**Rule**: Suffix with `_cb`, `_handler`, `_fn`, or `_func`.

```c
// GOOD:
typedef void (*timer_expire_cb)(void *data);
typedef int (*msg_recv_handler)(struct msg_header *hdr, void *payload);
void register_disconnect_cb(conn_disconnect_cb cb);

// BAD:
typedef void (*TimerCallback)(void *);     // CamelCase
typedef int (*on_message)(void *);          // JavaScript-style
```

### 1.7 File Naming

**Rule**: `snake_case.c` / `snake_case.h`. Prefix with module name for clarity.

```
// GOOD:
net_conn.c / net_conn.h
audio_encoder.c / audio_encoder.h
buf_manager.c / buf_manager.h

// BAD:
NetConn.c             // CamelCase
audioEncoder.c        // camelCase
bufmgr.c              // abbreviation without underscore separation
```

### 1.8 Header Guard

**Rule**: `__MODULE_FILENAME_H__` or `_MODULE_FILENAME_H_`, matching file path.

```c
// For file: include/net/conn.h
#ifndef __NET_CONN_H__
#define __NET_CONN_H__
...
#endif /* __NET_CONN_H__ */
```

---

## 2. Spelling Verification

### Process

For every new or changed identifier:
1. Split by underscores into individual words
2. Verify each word is a correctly spelled English word OR an entry in the standard abbreviation table (Section 3)
3. If neither → flag as spelling issue

### Severity

- Misspelling in **exported API** / **public header**: 🟡 Medium (becomes permanent once released)
- Misspelling in **local variable / static function**: 🟢 Low (localized impact)
- Misspelling matching a **different valid word**: 🟡 Medium (semantic confusion, e.g., `form` vs `from`, `statue` vs `status`)

---

## 3. Standard Abbreviations

Industry-standard abbreviations that need no comment or glossary entry:

### General Programming

| Abbr | Full | | Abbr | Full |
|------|------|---|------|------|
| `addr` | address | | `alloc` | allocate |
| `arg` | argument | | `async` | asynchronous |
| `attr` | attribute | | `buf` | buffer |
| `cb` | callback | | `cfg` | configuration |
| `cmd` | command | | `cnt` | count |
| `ctx` | context | | `cur` | current |
| `dealloc` | deallocate | | `desc` | descriptor |
| `dev` | device | | `dir` | directory |
| `en`/`dis` | enable/disable | | `env` | environment |
| `err` | error | | `eval` | evaluate |
| `fd` | file descriptor | | `fmt` | format |
| `fn`/`func` | function | | `hdr` | header |
| `idx` | index | | `info` | information |
| `init` | initialize | | `itr`/`iter` | iterator |
| `len` | length | | `lvl` | level |
| `max` | maximum | | `mgr` | manager |
| `min` | minimum | | `msg` | message |
| `nr`/`num` | number | | `obj` | object |
| `op`/`ops` | operation(s) | | `opt` | option |
| `param` | parameter | | `pkt` | packet |
| `pos` | position | | `prev` | previous |
| `prio` | priority | | `priv` | private |
| `proc` | process/procedure | | `ptr` | pointer |
| `ref` | reference | | `reg` | register |
| `req` | request | | `resp` | response |
| `ret` | return value | | `rx` | receive |
| `sem` | semaphore | | `seq` | sequence |
| `src` | source | | `dst` | destination |
| `stat`/`stats` | statistics | | `str` | string |
| `sync` | synchronous | | `sys` | system |
| `tmp`/`temp` | temporary | | `tx` | transmit |
| `val` | value | | `ver` | version |

### Embedded / Linux Specific

| Abbr | Full | | Abbr | Full |
|------|------|---|------|------|
| `clk` | clock | | `dma` | direct memory access |
| `drv` | driver | | `gpio` | general purpose I/O |
| `hw` | hardware | | `intr`/`irq` | interrupt |
| `ipc` | inter-process communication | | `mux` | multiplexer |
| `peri` | peripheral | | `phy` | physical (layer) |
| `pll` | phase-locked loop | | `pwr` | power |
| `rpc` | remote procedure call | | `rtc` | real-time clock |
| `spi` | serial peripheral interface | | `uart` | universal asynchronous receiver-transmitter |
| `wdt` | watchdog timer | | `xfer` | transfer |
| `enc` | encoder | | `dec` | decoder |
| `mcu` | microcontroller | | `soc` | system-on-chip |
| `osd` | on-screen display | | `isp` | image signal processor |
| `i2c` | inter-integrated circuit | | `nand` | NAND flash |
| `emmc` | embedded MMC | | `chn`/`ch` | channel |

### Network

| Abbr | Full | | Abbr | Full |
|------|------|---|------|------|
| `conn` | connection | | `sock` | socket |
| `svr`/`srv` | server | | `cli` | client |
| `pkt` | packet | | `frag` | fragment |
| `bcast` | broadcast | | `mcast` | multicast |
| `ack` | acknowledge | | `nak`/`nack` | negative acknowledge |

---

## 4. Common Misspelling List

Frequently encountered misspellings in embedded codebases. Flag these on sight:

| Wrong | Correct | | Wrong | Correct |
|-------|---------|---|-------|---------|
| `recieve` | receive | | `acheive` | achieve |
| `sucess` | success | | `faild`/`faile` | failed |
| `lenght` | length | | `widht` | width |
| `heigth` | height | | `destory` | destroy |
| `regist` | register | | `bindding` | binding |
| `inital` | initial | | `initalize` | initialize |
| `seperate` | separate | | `occured` | occurred |
| `reponse` | response | | `calulate` | calculate |
| `deamon` | daemon | | `priorty` | priority |
| `excute` | execute | | `paramter` | parameter |
| `syncronize` | synchronize | | `asynchrous` | asynchronous |
| `writting` | writing | | `bufffer` | buffer |
| `connnect` | connect | | `disconect` | disconnect |
| `hanlder` | handler | | `mangager` | manager |
| `configue` | configure | | `avaliable` | available |
| `interrrupt` | interrupt | | `periphal` | peripheral |
| `trasfer` | transfer | | `recored` | record |
| `timout` | timeout | | `retransmision` | retransmission |
| `packge` | package | | `mesage` | message |
| `unregist` | unregister | | `deinital` | deinitialize |
| `infomation` | information | | `notifiy` | notify |
| `resouces` | resources | | `threshhold` | threshold |
| `frequence` | frequency | | `pervious` | previous |

### Non-Standard Abbreviations (Flag These)

Abbreviations NOT in the standard table above that are sometimes seen but should be avoided or documented:

| Avoid | Prefer | Reason |
|-------|--------|--------|
| `cb_func` | `cb` or `_cb` suffix | Redundant — `cb` already means callback |
| `str_buf` → `strbuf` | `str_buf` | Must have underscore separation |
| `no` (as "number") | `num` or `nr` | `no` is ambiguous (also means "negative") |
| `chk` | `check` | Not universally recognized |
| `tbl` | `table` | Saves only 2 chars, loses clarity |
| `misc` | spell out or restructure | Vague catch-all name |
| `bak` | `backup` | Not standard |
| `del` | `delete` or `remove` | Ambiguous (also means "delegate") |

---

## 5. Anti-Patterns

### 5.1 Hungarian Notation

```c
// BAD — do not use type/scope prefixes:
int nCount;           // 'n' for integer
char *lpszName;       // Win32-style
DWORD dwFlags;        // Win32-style
int g_global_count;   // 'g_' for global (debatable — some projects allow this)
int m_member;         // 'm_' for member (C++ style, not Linux C)

// GOOD:
int count;
char *name;
uint32_t flags;
```

### 5.2 CamelCase in C

```c
// BAD:
void HandleIncomingMessage(void);
int frameCount;
struct StreamContext;

// GOOD:
void handle_incoming_message(void);
int frame_count;
struct stream_ctx;
```

### 5.3 Meaningless Names

```c
// BAD:
int data;       // what data?
void process(); // process what?
int flag;       // which flag?
int temp;       // OK only for truly temporary swap variable

// GOOD:
int frame_size;
void process_audio_frame();
int is_stream_active;
```

### 5.4 Overly Long Names

```c
// BAD — excessive detail in name:
int current_video_encoder_output_frame_buffer_remaining_size;

// GOOD — context is already clear from struct/function scope:
struct video_encoder {
    int out_buf_remain;  // clear within struct context
};
```
