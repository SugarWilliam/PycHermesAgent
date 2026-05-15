# Debugging Print Guide for Logic Bugs

Strategic print placements for narrowing logic bugs when static analysis leaves multiple possibilities.

**Key principle**: Do NOT guess. Add prints, run, collect evidence, then continue analysis.

---

## High-Value Print Placements

### 1. Branch Points — print which branch taken and why

```c
DBG("branch: cond=%d (a=%d b=%d)", condition, a, b);
```

### 2. Before/After Suspected Operation — print input and output

```c
DBG("BEFORE: state=%d input=%d", state, input);
result = process(input);
DBG("AFTER:  state=%d result=%d", state, result);
```

### 3. Cross-Module Boundaries — print data leaving A and entering B

```c
// Module A sending:
DBG("A->B: type=%d len=%d seq=%u", msg->type, msg->len, msg->seq);
// Module B receiving:
DBG("B<-A: type=%d len=%d seq=%u", msg->type, msg->len, msg->seq);
```

### 4. State Transitions — print old and new state

```c
DBG("STATE: %s -> %s (event=%s)", state_name(old), state_name(new), event_name(evt));
```

### 5. Loop Iterations — print counter and key variable

```c
DBG("loop[%d/%d]: key=%d accum=%ld", i, total, key, accumulator);
```

---

## Binary Bisection for Large Code Regions

1. Print at **midpoint** of suspected region
2. If correct: bug after midpoint → repeat in second half
3. If wrong: bug at/before midpoint → repeat in first half
4. Iterate until narrowed to 5-10 lines
