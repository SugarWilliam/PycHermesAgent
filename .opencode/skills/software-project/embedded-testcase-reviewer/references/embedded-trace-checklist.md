# Embedded Trace Checklist

Use this checklist while mapping each testcase to code.

## 1. Confirm the Active Product Path

Check whether behavior depends on:

- board type
- product model
- compile-time macros
- feature flags or capability sets
- flash or NVRAM configuration
- external MCU or companion firmware

If any of these control the path and the active setting is unknown, pause and ask.

## 2. Normalize the Testcase

Extract:

1. Preconditions
2. Trigger
3. Expected visible behavior
4. State transition implied by the testcase
5. Output owner: AP, MCU, bootloader, charger IC, sensor controller, or another component

## 3. Trace from Entry to Output

For each testcase, trace this chain:

1. Event source
   Examples:
   GPIO interrupt, task loop, RPC command, message callback, timer callback, wakeup reason, IRQ, charger-state report, network event
2. State update
   Examples:
   global flags, struct fields, bitmap bits, queue messages, persisted config, cached status
3. Decision logic
   Examples:
   state machine, switch-case, feature flag branch, board-type branch, owner-priority arbitration
4. Output emission
   Examples:
   GPIO set, I2C command, UART packet, SPI command, SDIO control, USB action, inter-chip message, codec command

Do not stop at a mid-layer helper unless that helper is the final observable behavior.

## 4. Peripheral-Oriented Questions

### GPIO

- Which function writes the GPIO?
- Is the write gated by a higher-level force mode or configuration?
- Is there a refresh call after state changes?

### I2C / SPI / UART / SDIO / USB

- Is the state only read, or does it produce a visible action?
- Is the command sent immediately or only cached?
- Is there a separate MCU/codec that owns the final output?

### Multi-Chip Systems

- Which chip decides the behavior?
- Which chip drives the hardware output?
- Is the interface message present?
- Is the receiving side code in this repository or missing?

## 5. RTOS / Linux Execution Questions

### FreeRTOS-style products

- Which task owns the state machine?
- Is the event handled in a queue, callback, timer, or polling loop?
- Does the state update happen without a follow-up refresh?

### Linux-style products

- Is behavior split across daemon, thread, IPC handler, driver, or user-space service?
- Does the state update occur in one process while the output is owned by another?
- Is the reviewed repository only one part of the visible behavior?

## 6. Common Embedded Review Pitfalls

Check for these repeatedly:

1. State updated but output not refreshed
2. Generic path and model-specific path implement different behavior
3. Macro-gated branch removes a feature required by testcase
4. App code assumes MCU will show behavior, but message is never sent
5. Loader or boot phase behavior is expected, but app code only sets a reboot flag
6. Runtime config stored in flash changes behavior, but current config value is unknown
7. One path handles running mode while standby path is separately gated and inconsistent

## 7. When to Stop and Ask Questions

Ask the user for more information if any of these block a confident verdict:

- target board or model is unclear
- active macro set is unknown
- expected behavior may be in missing MCU or bootloader code
- testcase wording implies hardware ownership outside the current repository
- multiple variants exist and the testcase does not specify which one applies

## 8. Minimum Evidence Checklist Per Testcase

Before finalizing a verdict, verify you have:

1. the likely entry point
2. the controlling state variable or message
3. the branch that should produce the behavior
4. the actual output function or command
5. either proof of existence or proof of absence/conflict