"""Builtin skill definitions for prompt and analysis categories."""

from __future__ import annotations

from pyc_hermes_agent.hermes_engine.skills.registry import SkillDefinition, SkillRegistry

BUILTIN_SKILLS: list[SkillDefinition] = [
    # --- Prompt Skills (E1) ---
    SkillDefinition(
        id="structured-report",
        name="Structured Report",
        category="prompt",
        description="Forces structured output with Introduction, Method, Results, Discussion, and Conclusion sections.",
        system_prompt_fragment=(
            "You must structure every response using the following sections: "
            "Introduction (state the problem and scope), Method (describe the approach taken), "
            "Results (present findings with data or evidence), Discussion (interpret results, "
            "compare alternatives, note limitations), and Conclusion (summarize key takeaways "
            "and actionable recommendations). Each section must have a clear heading. "
            "Do not omit any section even if brief."
        ),
    ),
    SkillDefinition(
        id="executive-summary",
        name="Executive Summary",
        category="prompt",
        description="Concise executive summary style with bullets, key metrics, and recommendations.",
        system_prompt_fragment=(
            "Respond in executive summary format. Lead with a one-sentence verdict. "
            "Follow with 3-7 bullet points covering key findings and metrics. "
            "Quantify impact wherever possible using numbers, percentages, or time estimates. "
            "End with a prioritized list of 2-4 concrete recommendations. "
            "Keep total length under 300 words. Avoid jargon and unnecessary detail."
        ),
    ),
    SkillDefinition(
        id="technical-detail",
        name="Technical Detail",
        category="prompt",
        description="Detailed technical writing with code examples and references.",
        system_prompt_fragment=(
            "Write in detailed technical style. Include precise terminology and definitions. "
            "Provide code examples, configuration snippets, or command-line invocations where relevant. "
            "Reference specific file paths, function names, or API endpoints. "
            "Explain trade-offs and edge cases. Use numbered steps for procedures. "
            "Cite sources or documentation links when making factual claims about tools or libraries."
        ),
    ),
    SkillDefinition(
        id="bilingual-output",
        name="Bilingual Output",
        category="prompt",
        description="Output in both English and Chinese (dual-language).",
        system_prompt_fragment=(
            "Produce all output in dual-language format. Write the full response first in English, "
            "then provide the complete equivalent in Chinese (简体中文) under a '---' separator. "
            "Both versions must convey identical meaning and structure. "
            "Technical terms may remain in English within the Chinese section where no standard "
            "translation exists. Maintain consistent formatting across both versions."
        ),
    ),
    # --- Analysis Skills (E2) ---
    SkillDefinition(
        id="swot-analysis",
        name="SWOT Analysis",
        category="analysis",
        description="SWOT framework: Strengths, Weaknesses, Opportunities, Threats.",
        system_prompt_fragment=(
            "Analyze using the SWOT framework. Create four clearly labeled sections: "
            "Strengths (internal advantages and capabilities), Weaknesses (internal limitations "
            "and risks), Opportunities (external favorable conditions and trends), and Threats "
            "(external challenges and competitive pressures). List 3-5 items per quadrant. "
            "For each item provide a brief explanation of why it belongs in that category. "
            "Conclude with a synthesis paragraph connecting the most critical cross-quadrant interactions."
        ),
    ),
    SkillDefinition(
        id="causal-reasoning",
        name="Causal Reasoning",
        category="analysis",
        description="Explicit causal chain reasoning from premise to conclusion.",
        system_prompt_fragment=(
            "Structure your reasoning as an explicit causal chain. Begin with clearly stated "
            "premises or observations. For each causal link, state the mechanism that connects "
            "cause to effect. Provide supporting evidence for each mechanism. Identify assumptions "
            "and potential confounders at each step. Present the final conclusion only after "
            "the full chain is established. Rate confidence in the overall chain as High, Medium, "
            "or Low based on the weakest link."
        ),
    ),
    SkillDefinition(
        id="comparison-matrix",
        name="Comparison Matrix",
        category="analysis",
        description="Structured comparison table with weighted scoring.",
        system_prompt_fragment=(
            "Present the comparison as a structured matrix. Define evaluation criteria as rows "
            "and options as columns. Assign a weight (1-5) to each criterion based on importance. "
            "Score each option per criterion on a 1-5 scale with brief justification. "
            "Calculate weighted totals. Present results in a markdown table. "
            "Below the table, summarize the top recommendation and note any criteria where "
            "the runner-up significantly outperforms the winner."
        ),
    ),
    SkillDefinition(
        id="risk-assessment",
        name="Risk Assessment",
        category="analysis",
        description="Risk identification with probability, impact, and mitigation strategies.",
        system_prompt_fragment=(
            "Perform a structured risk assessment. For each identified risk, provide: "
            "a clear description, probability rating (Low/Medium/High), impact rating "
            "(Low/Medium/High), a risk score (probability × impact mapped to 1-9), "
            "and a specific mitigation strategy. Present risks in descending order of risk score. "
            "Include at least one residual risk that remains after mitigation. "
            "Conclude with an overall risk posture summary."
        ),
    ),
]


def register_builtin_skills(registry: SkillRegistry) -> None:
    """Register all builtin skills into the given registry."""
    for skill in BUILTIN_SKILLS:
        registry.register(skill)
