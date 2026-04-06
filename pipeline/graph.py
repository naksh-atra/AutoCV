"""LangGraph state machine for the AutoCV pipeline + CLI entrypoint."""
import argparse
import sys
from pathlib import Path

# Add project root to path so pipeline imports work
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from langgraph.graph import StateGraph, END

from pipeline.state import PipelineState
from pipeline.nodes import (
    load_context,
    build_prompt,
    call_llm,
    sanitize_and_compile,
    score_ats_node,
    score_recruiter_node,
    check_threshold,
    refine_prompt,
    generate_report,
)


def build_graph():
    """Build the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    # Register nodes
    workflow.add_node("load_context", load_context)
    workflow.add_node("build_prompt", build_prompt)
    workflow.add_node("call_llm", call_llm)
    workflow.add_node("sanitize_and_compile", sanitize_and_compile)
    workflow.add_node("score_ats", score_ats_node)
    workflow.add_node("score_recruiter", score_recruiter_node)
    workflow.add_node("check_threshold", check_threshold)
    workflow.add_node("refine_prompt", refine_prompt)
    workflow.add_node("generate_report", generate_report)

    # Linear flow
    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "build_prompt")
    workflow.add_edge("build_prompt", "call_llm")
    workflow.add_edge("call_llm", "sanitize_and_compile")
    workflow.add_edge("sanitize_and_compile", "score_ats")
    workflow.add_edge("score_ats", "score_recruiter")
    workflow.add_edge("score_recruiter", "check_threshold")

    # Conditional edges from check_threshold
    workflow.add_conditional_edges(
        "check_threshold",
        lambda state: "refine" if not state["final"] else "report",
        {"refine": "refine_prompt", "report": "generate_report"},
    )

    # Loop back or end
    workflow.add_edge("refine_prompt", "build_prompt")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


def run_pipeline(jd_path: str, job_role: str, company: str):
    """Run the full pipeline."""
    app = build_graph()

    initial_state: PipelineState = {
        "jd_path": jd_path,
        "jd_text": "",
        "resume_latex": "",
        "job_role": job_role,
        "company": company,
        "knowledge_base": {},
        "current_prompt_rules": [],
        "_system_prompt": "",
        "_user_prompt": "",
        "_reverted": False,
        "tailored_latex": "",
        "pdf_path": "",
        "tex_path": "",
        "iteration": 0,
        "max_iterations": 3,
        "final": False,
        "ats_score": 0.0,
        "recruiter_score": 0.0,
        "ats_weaknesses": [],
        "ats_details": {},
        "recruiter_weaknesses": [],
        "recruiter_strengths": [],
        "ats_scratchpad": "",
        "recruiter_scratchpad": "",
        "refined_rules": [],
        "score_history": [],
        "report_text": "",
    }

    result = app.invoke(initial_state)
    return result


def main():
    parser = argparse.ArgumentParser(description="AutoCV Pipeline - Automated resume tailoring")
    parser.add_argument("--jd", required=True, help="Path to JD text file")
    parser.add_argument("--job-role", required=True, help="Job role for filename (e.g., AI_Engineer)")
    parser.add_argument("--company", required=True, help="Company name for filename (e.g., YABX)")
    args = parser.parse_args()

    jd_path = Path(args.jd)
    if not jd_path.is_absolute():
        jd_path = Path(__file__).resolve().parent.parent / jd_path

    if not jd_path.exists():
        print(f"Error: JD file not found: {jd_path}")
        sys.exit(1)

    print("=" * 60)
    print("AutoCV Pipeline - Starting")
    print("=" * 60)

    result = run_pipeline(str(jd_path), args.job_role, args.company)

    print("\n" + "=" * 60)
    print("Pipeline Complete")
    print("=" * 60)
    print(f"PDF: {result.get('pdf_path', 'N/A')}")
    print(f"Report: {result.get('report_text', '')[:200]}...")


if __name__ == "__main__":
    main()
