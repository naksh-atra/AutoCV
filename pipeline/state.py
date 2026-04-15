"""Pipeline state schema for LangGraph state machine."""
from typing import TypedDict, Optional


class PipelineState(TypedDict):
    """State tracked throughout the resume tailoring pipeline."""
    
    # Input
    jd_path: str                          # Path to JD file
    jd_text: str                          # Raw JD content
    resume_latex: str                     # Source resume template
    job_role: str                         # e.g., "AI_Engineer"
    company: str                          # e.g., "YABX"
    
    # Knowledge base
    knowledge_base: dict                  # Loaded from knowledge_base.json
    current_prompt_rules: list[str]       # Active rules for this iteration
    
    # Internal prompt storage
    _system_prompt: str                   # Built system prompt
    _user_prompt: str                     # Built user prompt
    _reverted: bool                       # Flag for score regression
    
    # LLM output
    tailored_latex: str                   # Raw LLM output
    pdf_path: str                         # Compiled PDF path
    tex_path: str                         # Saved .tex path
    
    # Loop control
    iteration: int                        # Current loop count (1-based)
    max_iterations: int                   # Default: 3
    final: bool                           # True = stop looping
    
    # Scoring
    ats_score: float                      # 0-10
    recruiter_score: float                # 0-10
    ats_weaknesses: list[str]             # Missing keywords, format issues
    ats_details: dict                     # Detailed ATS check results
    recruiter_weaknesses: list[str]       # Tone, metric, authenticity issues
    recruiter_strengths: list[str]        # What works well
    ats_scratchpad: str                   # CoT trace for debugging
    recruiter_scratchpad: str             # CoT trace for debugging
    
    # Refinement
    refined_rules: list[str]              # New rules from this iteration
    
    # History
    score_history: list[dict]             # [{iteration, ats, recruiter}]
    
    # Report
    report_text: str                      # Final report content
