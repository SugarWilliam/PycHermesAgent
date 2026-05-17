# Bug Analysis Report Template

Use this template for the final analysis report output.

```markdown
## Bug Analysis Report

### 1. Symptom Summary
- **Observed**: [what happens]
- **Expected**: [what should happen]
- **Trigger**: [always / intermittent / specific condition]

### 2. Log Analysis
- **Timeline**: [key events in chronological order]
- **Narrowed Region**: [file:function:line_range]
- **Key Evidence**: [specific log entries pointing to root cause]

### 3. Call-Chain Analysis
- **Entry Point**: [user action / message / timer / ISR that triggers the path]
- **Upward Chain**: caller_N -> ... -> caller_1 -> suspected_function
- **Downward Chain**: suspected_function -> callee_1 -> ... -> sink
- **Shared State**: [global variables / shared memory touched, with all accessors]
- **Divergence Point**: [exact line where actual behavior deviates from expected]

### 4. Hypotheses (Ranked)
| # | Hypothesis | Likelihood | Verification |
|---|-----------|------------|--------------|
| 1 | ... | High | ... |
| 2 | ... | Medium | ... |

### 5. Root Cause
- **Location**: [file:function:line]
- **Defective Code**: [code snippet]
- **Mechanism**: [why it fails]
- **Evidence**: [how symptoms match]

### 6. Suggested Fix
- **Code Change**: [fix snippet]
- **Rationale**: [why this fixes it]
- **Side Effects**: [risks or impacts]

### 7. Verification Plan
- [test steps to confirm fix]
- [edge cases to check]

### 8. Investigation Discipline Summary
- **Reproducibility**: [always / intermittent / not yet reproduced]
- **Recent Changes Checked**: [yes/no — which commits/diffs reviewed]
- **Working Reference Compared**: [yes/no — which reference used, key differences found]
- **Multi-Component Boundary Checked**: [yes/no — which boundaries instrumented, where data broke]
- **Fix Attempts**: [count — each attempt with result and what it ruled out]
- **Red Flags Caught**: [any premature fix urges or guessing impulses caught and corrected]
```
