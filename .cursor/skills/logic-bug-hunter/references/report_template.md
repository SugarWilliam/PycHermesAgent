# Logic Bug Report Templates

Two report formats depending on analysis confidence level.

---

## Format A: Debugging Required (Confidence < 100%)

Use when the bug cannot be 100% logically confirmed and requires dynamic tracing.

```markdown
## Logic Bug Analysis: Debugging Required

*Multiple possible execution paths and insufficient log evidence. Add the following debug prints and provide the resulting logs.*

### 1. Current Understanding & Hypothesis
- **Known Facts**: [what is currently established]
- **Unknown Branch/State**: [what exact value or path is missing]

### 2. Required Debug Prints
- **File**: `[filename]`
- **Function**: `[function_name]`
- **Insertion Point**: [exact line number or surrounding code]
- **Code to Add**:
  ```c
  [printf/DBG code tracking specific state/variables]
  ```
- **Rationale**: [Why this specific log will narrow down the root cause]

*(Do not output Root Cause or Fix sections until the logic loop is closed)*
```

---

## Format B: Full Analysis Report (Confidence = 100%)

Use when the logic loop is 100% closed.

```markdown
## Logic Bug Analysis Report

### 1. Behavioral Gap
- **Actual**: [what happens]
- **Expected**: [what should happen]
- **Gap Type**: [deterministic / state-dependent / intermittent / requirement mismatch]
- **Trigger**: [always / specific condition / sporadic]

### 2. Log Evidence Analysis
- **Last Correct Point**: [timestamp/line — last log showing correct behavior]
- **First Incorrect Point**: [timestamp/line — first log showing wrong behavior]
- **Variable Value Divergence**: [variable X was A, should have been B, at location Y]
- **Control Flow Evidence**: [which branches were taken vs expected]

### 3. Call-Chain Analysis
- **Entry Point**: [event that triggers the path]
- **Upward Chain**: caller_N → ... → suspected_function (with arg provenance)
- **Downward Chain**: suspected_function → callee_1 → ... → sink
- **Cross-Module Data Flow**: [shared state, all accessors, protocol compliance]
- **Divergence Point**: [exact line where behavior first deviates]

### 4. Hypotheses (Ranked)
| # | Hypothesis | Explains All Symptoms? | Likelihood | Verification |
|---|-----------|------------------------|------------|--------------|
| 1 | ... | Yes | High | ... |
| 2 | ... | Partial | Medium | ... |

### 5. Root Cause
- **Location**: [file:function:line]
- **Defective Code**: [snippet]
- **Mechanism**: [why it produces wrong behavior]
- **Symptom Explanation**: [how it causes each observed symptom]
- **Trigger Condition**: [always / precondition for intermittent]

### 6. Fix
- **Code Change**: [fix snippet]
- **Rationale**: [why this fixes the root cause]
- **Side Effects**: [risks or impacts]

### 7. Verification Plan
- [test to confirm fix]
- [edge case tests]
- [stress test for intermittent bugs]

### 8. Investigation Discipline Summary
- **Reproducibility**: [always / intermittent / not yet reproduced]
- **Recent Changes Checked**: [yes/no — which commits/diffs reviewed]
- **Working Reference Compared**: [yes/no — which reference used, key differences found]
- **Fix Attempts**: [count — each attempt with result and what it ruled out]
- **Red Flags Caught**: [any premature fix urges or guessing impulses caught and corrected]
```
