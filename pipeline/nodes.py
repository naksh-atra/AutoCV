"""Pipeline node functions for LangGraph state machine."""
import re
import json
import time
from pathlib import Path

from pipeline.state import PipelineState
from pipeline.scorers import (
    score_ats,
    build_ats_prompt,
    build_recruiter_prompt,
    build_synthesizer_prompt,
    parse_json_from_llm
)


def load_context(state: PipelineState) -> PipelineState:
    """Load JD, resume template, and knowledge base into state."""
    jd_path = Path(state["jd_path"])
    state["jd_text"] = jd_path.read_text(encoding="utf-8")
    
    project_root = Path(__file__).resolve().parent.parent
    resume_path = project_root.parent / "resume_template.tex"
    state["resume_latex"] = resume_path.read_text(encoding="utf-8")
    
    kb_path = project_root / "knowledge_base.json"
    state["knowledge_base"] = json.loads(kb_path.read_text(encoding="utf-8"))
    
    pipeline_config = state["knowledge_base"]["pipeline_config"]
    state["max_iterations"] = pipeline_config["max_iterations"]
    state["iteration"] = 0
    state["final"] = False
    state["current_prompt_rules"] = []
    state["score_history"] = []
    
    for category, rules in state["knowledge_base"]["prompt_rules"].items():
        state["current_prompt_rules"].extend(rules)
    
    print(f"[Pipeline] Loaded JD: {jd_path.name}")
    print(f"[Pipeline] Job role: {state['job_role']}")
    print(f"[Pipeline] Company: {state['company']}")
    
    return state


def build_prompt(state: PipelineState) -> PipelineState:
    """Build system + user prompts with current rules + domain detection."""
    from prompt import SYSTEM_PROMPT, build_prompt as original_build_prompt
    
    jd_text = state["jd_text"]
    resume_latex = state["resume_latex"]
    
    system_prompt, user_prompt = original_build_prompt(resume_latex, jd_text)
    
    domain_rules = state["knowledge_base"]["domain_specific_rules"]
    jd_lower = jd_text.lower()
    
    for domain, config in domain_rules.items():
        if any(trigger.lower() in jd_lower for trigger in config["triggers"]):
            for keyword in config["keywords"]:
                rule = f"Include '{keyword}' in skills or bullets if JD mentions {domain}."
                if rule not in state["current_prompt_rules"]:
                    state["current_prompt_rules"].append(rule)
    
    # Inject accumulated rules into the system prompt
    if state["current_prompt_rules"]:
        rules_section = "\n\n### ADDITIONAL RULES FOR THIS ITERATION:\n"
        for i, rule in enumerate(state["current_prompt_rules"], 1):
            rules_section += f"{i}. {rule}\n"
        system_prompt = system_prompt.rstrip() + rules_section
    
    state["_system_prompt"] = system_prompt
    state["_user_prompt"] = user_prompt
    
    print(f"[Pipeline] Iteration {state['iteration'] + 1}: Prompt built with {len(state['current_prompt_rules'])} rules")
    
    return state


def call_llm(state: PipelineState) -> PipelineState:
    """Call Groq API to generate tailored resume."""
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from llm.groq_provider import GroqProvider
    from dotenv import load_dotenv
    
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    
    provider = GroqProvider(api_key=api_key)
    system_prompt = state["_system_prompt"]
    user_prompt = state["_user_prompt"]
    
    models = state["knowledge_base"]["models"]
    model = models["resume_generation"]
    temperature = state["knowledge_base"]["pipeline_config"]["temperature_generation"]
    
    print(f"[Pipeline] Calling Groq ({model}) for resume generation...")
    response = provider.chat(system_prompt, user_prompt, model=model, temperature=temperature)
    
    state["tailored_latex"] = response
    
    print(f"[Pipeline] LLM response received ({len(response)} chars)")
    
    return state


def sanitize_and_compile(state: PipelineState) -> PipelineState:
    """Sanitize LLM output and compile to PDF."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from sanitize import sanitize
    from compile import compile_to_pdf
    
    sanitized = sanitize(state["tailored_latex"])
    
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "CVs"
    output_dir.mkdir(exist_ok=True)
    
    job_role = state["job_role"]
    company = state["company"]
    base_name = f"Nakshatra_{job_role}_{company}"
    
    tex_path = output_dir / f"{base_name}.tex"
    pdf_path = output_dir / f"{base_name}.pdf"
    
    tex_path.write_text(sanitized, encoding="utf-8")
    
    print(f"[Pipeline] Compiling PDF...")
    try:
        compiled_pdf = compile_to_pdf(sanitized, output_dir=output_dir, output_name=f"{base_name}.pdf")
        state["tex_path"] = str(tex_path)
        state["pdf_path"] = str(compiled_pdf)
        print(f"[Pipeline] PDF generated: {compiled_pdf.name}")
    except Exception as e:
        print(f"[Pipeline] WARNING: PDF compilation failed: {e}")
        state["pdf_path"] = ""
        state["tex_path"] = str(tex_path)
    
    return state


def score_ats_node(state: PipelineState) -> PipelineState:
    """Run rule-based ATS scoring."""
    result = score_ats(
        state["tailored_latex"],
        state["jd_text"],
        state["knowledge_base"]
    )
    
    state["ats_score"] = result["score"]
    state["ats_weaknesses"] = result["weaknesses"]
    state["ats_details"] = result["details"]
    state["ats_scratchpad"] = result["scratchpad"]
    
    print(f"[Pipeline] ATS Score: {result['score']}/10")
    if result["weaknesses"]:
        for w in result["weaknesses"]:
            print(f"  - {w}")
    
    return state


def score_recruiter_node(state: PipelineState) -> PipelineState:
    """Run LLM-based recruiter scoring with forced CoT."""
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from llm.groq_provider import GroqProvider
    from dotenv import load_dotenv
    
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    
    provider = GroqProvider(api_key=api_key)
    models = state["knowledge_base"]["models"]
    model = models["recruiter_scoring"]
    temperature = state["knowledge_base"]["pipeline_config"]["temperature_scoring"]
    
    from pipeline.scorers import build_recruiter_prompt
    prompt = build_recruiter_prompt(
        state["jd_text"],
        state["tailored_latex"],
        state["job_role"],
        state["company"]
    )
    
    system_prompt = """You are a senior technical recruiter evaluating a resume. Follow the instructions carefully. Use a <scratchpad> block for your reasoning, then output ONLY JSON."""
    
    print(f"[Pipeline] Calling Groq ({model}) for recruiter scoring...")
    response = provider.chat(system_prompt, prompt, model=model, temperature=temperature)
    
    parsed = parse_json_from_llm(response)
    
    state["recruiter_score"] = parsed.get("recruiter_score", 0)
    state["recruiter_strengths"] = [parsed.get("strengths", "")]
    state["recruiter_weaknesses"] = [parsed.get("weaknesses", "")]
    state["recruiter_scratchpad"] = parsed.get("_scratchpad", "")
    
    print(f"[Pipeline] Recruiter Score: {state['recruiter_score']}/10")
    
    return state


def check_threshold(state: PipelineState) -> PipelineState:
    """Check if scores meet threshold or max iterations reached."""
    state["iteration"] += 1
    
    config = state["knowledge_base"]["pipeline_config"]
    ats_threshold = config["ats_threshold"]
    recruiter_threshold = config["recruiter_threshold"]
    
    score_entry = {
        "iteration": state["iteration"],
        "ats": state["ats_score"],
        "recruiter": state["recruiter_score"]
    }
    state["score_history"].append(score_entry)
    
    if state["iteration"] > 1:
        prev = state["score_history"][-2]
        if (state["ats_score"] < prev["ats"] and 
            state["recruiter_score"] < prev["recruiter"]):
            print(f"[Pipeline] Score regression detected — stopping")
            state["final"] = True
            state["_reverted"] = True
            return state
    
    if (state["ats_score"] >= ats_threshold and 
        state["recruiter_score"] >= recruiter_threshold):
        print(f"[Pipeline] Threshold met (ATS >= {ats_threshold}, Recruiter >= {recruiter_threshold})")
        state["final"] = True
    elif state["iteration"] >= state["max_iterations"]:
        print(f"[Pipeline] Max iterations ({state['max_iterations']}) reached")
        state["final"] = True
    else:
        print(f"[Pipeline] Below threshold — refining prompt (iteration {state['iteration']}/{state['max_iterations']})")
    
    return state


def refine_prompt(state: PipelineState) -> PipelineState:
    """Convert weaknesses into new prompt rules."""
    new_rules = []
    
    for weakness in state["ats_weaknesses"]:
        if "Missing" in weakness and "keywords" in weakness.lower():
            keywords = weakness.split(":")[-1].strip()
            new_rules.append(f"CRITICAL: Add these missing keywords to skills or bullets: {keywords}")
        elif "Missing standard headers" in weakness:
            new_rules.append("CRITICAL: Ensure ALL standard section headers are present: WORK EXPERIENCE, EDUCATION, TECHNICAL SKILLS, PROJECTS")
        elif "Multi-column" in weakness:
            new_rules.append("CRITICAL: Use single-column layout only — no multicols or multicol")
        elif "Tables detected" in weakness:
            new_rules.append("CRITICAL: Remove all tables — use plain text lists instead")
        elif "Images detected" in weakness:
            new_rules.append("CRITICAL: Remove all images and graphics")
        elif "Timeline" in weakness:
            new_rules.append("CRITICAL: Ensure complete timeline with all three work experience entries")
        elif "Degree" in weakness or "knockout" in weakness.lower():
            new_rules.append("CRITICAL: Explicitly mention BTech degree in Education section")
    
    for weakness in state["recruiter_weaknesses"]:
        weakness_lower = weakness.lower()
        if "robotic" in weakness_lower or "llm" in weakness_lower:
            new_rules.append("CRITICAL: Use natural, idiosyncratic language — avoid corporate speak and LLM-generated phrasing")
        if "over-quantification" in weakness_lower or "built 80%" in weakness_lower:
            new_rules.append("CRITICAL: NO personal contribution metrics — measure IMPACT only (latency, cost, accuracy)")
        if "xyz formula" in weakness_lower or "metric" in weakness_lower:
            new_rules.append("CRITICAL: Front-load metrics in first 3 words of every bullet using XYZ formula")
        if "compliance" in weakness_lower or "hipaa" in weakness_lower or "gdpr" in weakness_lower:
            new_rules.append("CRITICAL: Add compliance/data security keywords: data anonymization, secure handling, PII/PHI protection")
        if "frontend" in weakness_lower or "react" in weakness_lower or "vue" in weakness_lower:
            new_rules.append("CRITICAL: Include at least one frontend UI bullet with API integration")
        if "accuracy" in weakness_lower and "wrong" in weakness_lower:
            new_rules.append("CRITICAL: Use domain-appropriate metrics — precision/recall for RAG, latency for APIs, not accuracy for everything")
    
    state["refined_rules"] = new_rules
    state["current_prompt_rules"].extend(new_rules)
    
    print(f"[Pipeline] Added {len(new_rules)} refinement rules:")
    for rule in new_rules:
        print(f"  + {rule}")
    
    return state


def generate_report(state: PipelineState) -> PipelineState:
    """Generate final score report."""
    lines = []
    lines.append(f"=" * 60)
    lines.append(f"AutoCV Pipeline Report")
    lines.append(f"=" * 60)
    lines.append(f"JD: {state['job_role']} at {state['company']}")
    lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    lines.append(f"FINAL SCORES")
    lines.append(f"-" * 30)
    lines.append(f"ATS Score: {state['ats_score']}/10")
    lines.append(f"Recruiter Score: {state['recruiter_score']}/10")
    lines.append(f"Iterations: {state['iteration']}")
    lines.append(f"")
    
    if state.get("_reverted"):
        lines.append(f"NOTE: Score regression detected — reverted to best iteration")
        lines.append(f"")
    
    lines.append(f"ITERATION HISTORY")
    lines.append(f"-" * 30)
    for entry in state["score_history"]:
        lines.append(
            f"  Iteration {entry['iteration']}: "
            f"ATS {entry['ats']}/10 | Recruiter {entry['recruiter']}/10"
        )
    lines.append(f"")
    
    if state["ats_weaknesses"]:
        lines.append(f"ATS WEAKNESSES")
        lines.append(f"-" * 30)
        for w in state["ats_weaknesses"]:
            lines.append(f"  - {w}")
        lines.append(f"")
    
    if state["recruiter_strengths"]:
        lines.append(f"STRENGTHS")
        lines.append(f"-" * 30)
        for s in state["recruiter_strengths"]:
            lines.append(f"  {s}")
        lines.append(f"")
    
    if state["recruiter_weaknesses"]:
        lines.append(f"WEAKNESSES")
        lines.append(f"-" * 30)
        for w in state["recruiter_weaknesses"]:
            lines.append(f"  {w}")
        lines.append(f"")
    
    if state["refined_rules"]:
        lines.append(f"REFINED RULES ADDED")
        lines.append(f"-" * 30)
        for r in state["refined_rules"]:
            lines.append(f"  + {r}")
        lines.append(f"")
    
    config = state["knowledge_base"]["pipeline_config"]
    ats_met = state["ats_score"] >= config["ats_threshold"]
    rec_met = state["recruiter_score"] >= config["recruiter_threshold"]
    
    if ats_met and rec_met:
        recommendation = "Good for application"
    elif state["ats_score"] >= 7.0 and state["recruiter_score"] >= 6.0:
        recommendation = "Manual review recommended"
    else:
        recommendation = "Significant JD mismatch — manual revision needed"
    
    lines.append(f"RECOMMENDATION: {recommendation}")
    lines.append(f"")
    lines.append(f"OUTPUT FILES")
    lines.append(f"-" * 30)
    lines.append(f"PDF: {state['pdf_path']}")
    lines.append(f"LaTeX: {state['tex_path']}")
    lines.append(f"")
    lines.append(f"=" * 60)
    
    report_text = "\n".join(lines)
    state["report_text"] = report_text
    
    output_dir = Path(state["tex_path"]).parent
    report_path = output_dir / f"Nakshatra_{state['job_role']}_{state['company']}_report.txt"
    report_path.write_text(report_text, encoding="utf-8")
    
    print(f"[Pipeline] Report saved: {report_path.name}")
    print(f"[Pipeline] {report_text}")
    
    return state
