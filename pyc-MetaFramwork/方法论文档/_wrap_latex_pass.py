#!/usr/bin/env python3
"""One-pass: wrap bare LaTeX lines and \\begin{aligned}/cases blocks in $$ ... $$"""
import re
from pathlib import Path

PATH = Path(__file__).resolve().parent / "第一部_跨学科数学建模方法论体系（核心框架）.md"


def is_bare_latex_line(s: str) -> bool:
    if not s or s.startswith("|"):
        return False
    if s.startswith(("- ", "> ", "#")):
        return False
    if re.match(r"^\d+\.\s", s):
        return False
    if s.startswith("$"):
        return False
    # Pure latex command
    if re.match(r"^\\[a-zA-Z]", s):
        return True
    if re.search(r"[\u4e00-\u9fff]", s):
        return False
    # Identifier + heavy LaTeX (X_\infty \sim, Corr, etc.)
    if re.match(
        r"^[A-Za-z_][^\n]*\\(mathcal|text|mathbb|sin|cos|exp|log|ln|sum|int|frac|partial|Delta|sigma|omega|tau|theta|psi|rho|ell|nabla|mathbf|boldsymbol|hat|bar|tilde|infty|sim|approx|propto|mathrm)",
        s,
    ):
        return True
    if re.match(r"^[A-Za-z][^:\n]*\\frac", s):
        return True
    # p(\theta,...)= Bayesian posteriors starting with p(
    if re.match(r"^[a-z]\(.*\)\s*\\propto", s):
        return True
    return False


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_fence = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue

        # \begin{aligned} | cases | gather | equation
        m_env = re.match(r"^\s*\\begin\{(aligned|cases|gather|equation|multline)\}", stripped)
        if m_env:
            env = m_env.group(1)
            block_lines = [line]
            i += 1
            found_end = False
            while i < len(lines):
                block_lines.append(lines[i])
                if f"\\end{{{env}}}" in lines[i]:
                    found_end = True
                    i += 1
                    break
                i += 1
            inner_full = "\n".join(block_lines).strip()
            if inner_full.startswith("$$") or inner_full.endswith("$$"):
                out.extend(block_lines)
                continue
            indent = re.match(r"^(\s*)", block_lines[0]).group(1)
            out.append(indent + "$$")
            out.extend(block_lines)
            out.append(indent + "$$")
            continue

        # Known broken MLE table → single display equation
        if stripped.startswith("| \\hat{\\theta}") and i + 1 < len(lines) and "---" in lines[i + 1]:
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            indent = re.match(r"^(\s*)", line).group(1)
            eq = (
                r"\hat{\theta} = -\frac{1}{\Delta t} \ln\left(\frac{\sum_{t=1}^{T-1}(X_{t+1}-\bar{X})(X_t-\bar{X})}"
                r"{\sum_{t=1}^{T-1}(X_t-\bar{X})^2}\right)"
            )
            out.append(f"{indent}$${eq}$$")
            i = j
            continue

        if is_bare_latex_line(stripped):
            indent = re.match(r"^(\s*)", line).group(1)
            out.append(f"{indent}$${stripped}$$")
            i += 1
            continue

        out.append(line)
        i += 1

    PATH.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {PATH.name}, lines {len(lines)} -> {len(out)}")


if __name__ == "__main__":
    main()
