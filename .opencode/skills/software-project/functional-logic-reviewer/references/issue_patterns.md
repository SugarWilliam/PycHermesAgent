# Common Issue Patterns and Detection Methods

This document describes common issue patterns found in code changes and methods to detect them.

## 1. Logic Errors

### 1.1 Condition Reversal

**Pattern**: Condition is inverted or compared incorrectly

**Detection Method**:
1. Identify all if/else conditions in the change
2. Check if the condition logic matches the intent
3. Look for: `if (a == b)` vs `if (a != b)`, `if (a > b)` vs `if (a < b)`

**Example**:
```cpp
// Bug: Should be < instead of >
if (index > array_size)  // Wrong: always false for valid index
    return ERROR;

// Correct:
if (index >= array_size)
    return ERROR;
```

### 1.2 Operator Error

**Pattern**: Wrong operator used (assignment instead of comparison, bitwise instead of logical, etc.)

**Detection Method**:
1. Search for `=` in conditions (should be `==`)
2. Check bitwise vs logical operators
3. Check shift operators

**Example**:
```cpp
// Bug: Assignment in condition
if (ptr = NULL)  // Wrong: assigns NULL instead of comparing
    return ERROR;

// Correct:
if (ptr == NULL)
    return ERROR;
```

### 1.3 Off-By-One Error

**Pattern**: Boundary condition is wrong by one

**Detection Method**:
1. Identify array/list access patterns
2. Check all index calculations
3. Compare with size/length variables

**Example**:
```cpp
// Bug: Off-by-one
for (int i = 0; i <= size; i++)  // Wrong: accesses size index
    array[i] = 0;

// Correct:
for (int i = 0; i < size; i++)
    array[i] = 0;
```

## 2. State Machine Issues

### 2.1 Missing State Transition

**Pattern**: A valid state transition is not implemented

**Detection Method**:
1. List all valid states
2. List all possible transitions
3. Verify each transition is implemented

**Detection Code**:
```python
def check_missing_transitions(state_machine):
    valid_transitions = get_valid_transitions(state_machine)
    implemented = get_implemented_transitions(state_machine)
    missing = valid_transitions - implemented
    return missing
```

### 2.2 Invalid State Transition

**Pattern**: A transition to an invalid state is allowed

**Detection Method**:
1. Check transition target states
2. Verify all target states are valid

### 2.3 State Not Reset

**Pattern**: State is not properly reset between operations

**Detection Method**:
1. Check state initialization
2. Check state cleanup after operations
3. Look for residual state in subsequent operations

## 3. Transaction Issues

### 3.1 Incomplete Transaction

**Pattern**: Multi-step operation doesn't handle partial failure

**Detection Method**:
1. Identify multi-step operations
2. Check if all steps must succeed together
3. Verify rollback/recovery logic exists

**Example**:
```cpp
// Bug: Non-transactional operation
void deleteUser(int userId) {
    db.deleteUser(userId);          // Step 1: Delete from DB
    cache.remove(userId);           // Step 2: Remove from cache
    sendNotification(userId);       // Step 3: Send notification
    // If step 3 fails, user is deleted but no notification sent
}

// Correct: Two-phase or rollback
void deleteUser(int userId) {
    db.startTransaction();
    try {
        db.deleteUser(userId);
        cache.remove(userId);
        sendNotification(userId);
        db.commit();
    } catch (...) {
        db.rollback();  // Restore state
        throw;
    }
}
```

### 3.2 Resource Leak in Transaction

**Pattern**: Resources are not cleaned up if transaction fails

**Detection Method**:
1. Identify resource allocation (malloc, file open, lock, etc.)
2. Check all exit paths clean up resources
3. Look for: return/throw without cleanup

### 3.3 Resource Leak on Any Exit Path

**Pattern**: Function acquires resources (`fopen`, `open`, `malloc`, `lock`, etc.) but one or more exit points (`return`, `throw`, `goto`, or macro-generated exits) bypass the resource-release code — releasing resources on some paths but leaking on others. Most commonly missed on the **success path**.

**Why it's missed**: Reviewers instinctively verify error paths. A `return OK` / `return 0` looks correct in isolation and is rarely scrutinized for resource leaks.

**Detection Method**:
1. Identify all non-RAII resources acquired inside the function (`fopen`, `open`, `malloc`, `pthread_mutex_lock`, etc.)
2. List **every** exit point in the function: `return`, `throw`, `goto`, and macro-generated exits
3. Determine which macros expand to `goto` (reach the centralized release site) vs. which expand to `return` directly (skip it)
4. For each exit point that is not the final statement after the resource-release site, verify it releases all resources acquired above it
5. **RAII + manual mix**: if RAII manages some resources but others are managed manually, the RAII destructor runs on all exits — the manual resource is only freed where explicitly coded; any exit that skips the release site leaks it

**Example Bug**:
```c
int upload_file(const char *path)
{
    int ret_code = OK;
    FILE *fp = fopen(path, "rb");         // resource acquired
    CHK_ERR(fp, ERR_OPEN, "open failed"); // expands to goto cleanup on NULL

    // ... upload ...

    if (http_code >= 200 && http_code <= 299) {
        return OK;        // BUG: fp never closed — EMFILE after sustained calls
    }
    ret_code = ERR_HTTP;

cleanup:
    if (fp) fclose(fp);   // only reached on error path
    return ret_code;
}
```

**Correct Fix** — set the return value and fall through to the release site:
```c
    if (http_code >= 200 && http_code <= 299) {
        ret_code = OK;    // set value, fall through to release
    } else {
        ret_code = ERR_HTTP;
    }
cleanup:
    if (fp) fclose(fp);
    return ret_code;
```

**Special risk — RAII + manual mix**: C++ RAII destructors run on all exits, giving a false sense of safety. If the RAII class manages *some* handles (e.g., curl, socket) but `FILE *fp` is managed manually, any early exit leaks `fp` even though RAII resources are properly released.

## 4. Concurrency Issues

### 4.1 Race Condition

**Pattern**: Multiple threads access shared data without synchronization

**Detection Method**:
1. Identify shared data (global variables, heap objects)
2. Check access patterns from multiple threads
3. Verify synchronization exists

**Detection Code**:
```python
def detect_race_condition(shared_vars, thread_functions):
    for var in shared_vars:
        accesses = []
        for func in thread_functions:
            if var in func.writes:
                accesses.append((func, 'write'))
            elif var in func.reads:
                accesses.append((func, 'read'))
        
        # Check if unprotected concurrent access
        has_write = any(a[1] == 'write' for a in accesses)
        if len(accesses) > 1 and has_write:
            # Potential race if not protected
            warn(f"Potential race on {var}")
```

### 4.2 Deadlock

**Pattern**: Two or more threads wait for each other indefinitely

**Detection Method**:
1. Identify all locks acquired
2. Check lock ordering is consistent
3. Look for nested lock acquisition

**Example**:
```cpp
// Bug: Potential deadlock
void funcA() {
    lock(mutex1);     // Acquires mutex1
    funcB();          // May acquire mutex2
}

void funcB() {
    lock(mutex2);     // Acquires mutex2
    lock(mutex1);     // Deadlock if called while holding mutex1
}
```

### 4.3 Lost Wakeup

**Pattern**: Signal/wakeup is sent before wait, and is lost

**Detection Method**:
1. Check condition variable usage
2. Verify signal is not sent before wait

**Example**:
```cpp
// Bug: Lost wakeup
pthread_mutex_lock(&mutex);
while (!condition) {
    pthread_cond_wait(&cond, &mutex);  // May wait forever
}
// Signal sent before this thread reaches wait is lost
pthread_mutex_unlock(&mutex);

// Correct: Use while loop with condition check
```

## 5. Memory Issues

### 5.1 Memory Leak

**Pattern**: Allocated memory is not freed

**Detection Method**:
1. Track all malloc/new
2. Track all free/delete
3. Check for unmatched pairs

### 5.2 Use After Free

**Pattern**: Pointer is used after memory is freed

**Detection Method**:
1. Track pointer lifetime
2. Check for use after free

### 5.3 Double Free

**Pattern**: Memory is freed twice

**Detection Method**:
1. Track all free calls
2. Check for duplicate frees

## 6. Resource Issues

### 6.1 File Handle Leak

**Pattern**: File is opened but not closed

**Detection Method**:
1. Track fopen/open calls
2. Track close calls
3. Check for unmatched pairs

### 6.2 Connection Leak

**Pattern**: Network/database connection not closed

**Detection Method**:
1. Track connect calls
2. Track disconnect/close calls
3. Check error paths close connections

## 7. Boundary Issues

### 7.1 NULL Pointer Dereference

**Pattern**: Pointer is used without NULL check

**Detection Method**:
1. Identify pointer dereferences
2. Check for NULL checks before use

### 7.2 Buffer Overflow

**Pattern**: Write beyond buffer boundary

**Detection Method**:
1. Identify buffer allocations
2. Check all write operations
3. Verify bounds checking

### 7.3 Integer Overflow

**Pattern**: Integer operation overflows

**Detection Method**:
1. Identify integer operations
2. Check for overflow-prone operations
3. Verify bounds checking or overflow detection

## 8. Configuration Issues

### 8.1 Inconsistent Configuration

**Pattern**: Same configuration stored in multiple places with different values

**Detection Method**:
1. Identify configuration sources
2. Check for consistency

### 8.2 Default Value Error

**Pattern**: Wrong default value used

**Detection Method**:
1. Identify default value usage
2. Verify against specification

## 9. Error Handling Issues

### 9.1 Silent Failure

**Pattern**: Error is detected but not handled or logged

**Detection Method**:
1. Identify error detection points
2. Check error handling paths
3. Look for swallowed exceptions

### 9.2 Overly Broad Catch

**Pattern**: Catching exceptions too broadly

**Detection Method**:
1. Identify catch blocks
2. Check exception types
3. Verify specific exception handling

### 9.3 Error Information Loss

**Pattern**: Original error information is lost

**Detection Method**:
1. Check exception wrapping
2. Verify error context is preserved

## 10. Timing Issues

### 10.1 Timeout Handling

**Pattern**: Timeout occurs but not handled correctly

**Detection Method**:
1. Identify timeout configurations
2. Check timeout handling paths
3. Verify cleanup on timeout

### 10.2 Order Dependency

**Pattern**: Operations must be in specific order

**Detection Method**:
1. Identify order-dependent operations
2. Check ordering enforcement
3. Verify error on wrong order
