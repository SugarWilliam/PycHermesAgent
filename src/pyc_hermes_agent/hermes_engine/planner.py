"""Minimal planning and decomposition helpers for the Hermes agent loop."""

from __future__ import annotations

from pyc_hermes_agent.contracts import AgentPlan, ChatMessage, PlanStep, ToolDefinition


def build_agent_plan(messages: list[ChatMessage], tools: list[ToolDefinition]) -> AgentPlan | None:
    latest_user_message = _latest_user_message(messages)
    if latest_user_message is None:
        return None

    latest_text = latest_user_message.content.strip()
    if not latest_text:
        return None

    if not _should_plan(latest_text, tools):
        return None

    tool_names = {tool.name for tool in tools if tool.name}
    steps: list[PlanStep] = [
        PlanStep(
            step_id="understand",
            kind="understand",
            description="Confirm the user's request and identify what output is needed.",
        )
    ]

    if "formal_analysis" in tool_names and _should_plan_formal_analysis(latest_text):
        steps.append(
            PlanStep(
                step_id="formal-analysis",
                kind="tool",
                description="Use formal_analysis if structured methodology review or evidence grading is needed.",
            )
        )

    steps.append(
        PlanStep(
            step_id="respond",
            kind="respond",
            description="Return a concise final answer grounded in the latest available evidence and tool results.",
        )
    )

    return AgentPlan(
        summary=_plan_summary(latest_text, has_tool_step=any(step.kind == "tool" for step in steps)),
        steps=steps,
    )


def build_plan_message(plan: AgentPlan | None) -> ChatMessage | None:
    if plan is None or not plan.steps:
        return None

    lines = ["Execution plan:", f"Summary: {plan.summary}"]
    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"{index}. [{step.kind}] {step.description}")
    return ChatMessage(role="system", content="\n".join(lines))


def _latest_user_message(messages: list[ChatMessage]) -> ChatMessage | None:
    for message in reversed(messages):
        if message.role == "user":
            return message
    return None


def _should_plan_formal_analysis(text: str) -> bool:
    lowered = text.lower()
    triggers = (
        "formal analysis",
        "evidence",
        "method",
        "causal",
        "pagerank",
        "reasonableness",
        "logic review",
    )
    return any(trigger in lowered for trigger in triggers)


def _should_plan(text: str, tools: list[ToolDefinition]) -> bool:
    lowered = text.lower()
    if _should_plan_formal_analysis(text):
        return True
    if any(keyword in lowered for keyword in ("plan", "steps", "decompose", "workflow", "approach")):
        return True
    if len(lowered.split()) >= 18:
        return True
    tool_names = {tool.name for tool in tools if tool.name}
    if "formal_analysis" in tool_names and any(keyword in lowered for keyword in ("analyze", "analysis", "review")):
        return True
    return False


def _plan_summary(text: str, *, has_tool_step: bool) -> str:
    if has_tool_step:
        return "Review the request, use the right tool only if needed, then answer directly."
    return "Review the request, reason over available context, then answer directly."


__all__ = ["AgentPlan", "PlanStep", "build_agent_plan", "build_plan_message"]
