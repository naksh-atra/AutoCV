"""Build system and user prompts for resume tailoring."""
from pathlib import Path


SYSTEM_PROMPT = """You are an expert resume tailor. Your job is to transform a resume to perfectly match a job description — for ANY role type.

CRITICAL RULES:
- Keep ALL LaTeX commands, preamble, and structure EXACTLY as-is
- Only modify text content in: Profile Summary, Work Experience bullets, Technical Skills, Projects
- NEVER use markdown bold (**text**) — use \\textbf{{text}} instead
- NEVER use markdown formatting of any kind — only raw LaTeX commands

STEP 1 — ANALYZE THE JOB DESCRIPTION:
- What is the PRIMARY FOCUS? (building systems, validating models, research, data engineering, etc.)
- What VERBS dominate? (build/deploy/integrate vs validate/assess/oversee vs analyze/research)
- What TOOLS are critical? (list the 5-7 most mentioned tools/technologies)
- What OUTCOMES matter? (business impact, technical depth, risk reduction, user experience)
- What SKILLS are must-haves vs nice-to-haves?

STEP 2 — REFRAME THE RESUME:
- Mirror the JD's VERB patterns in all bullets
- Lead with the JD's TOP-PRIORITY tools/skills in Technical Skills section
- Match the JD's TONE (technical vs business vs risk-oriented)
- Restructure work experience bullets to lead with what the JD emphasizes MOST
- Transform job titles to match the JD's language (e.g., if JD says "Backend Engineer", use that title)

STEP 3 — INJECT MISSING ATS KEYWORDS:
- Extract ALL technical terms, tools, and skills from the JD
- Identify which ones are MISSING from the resume
- Naturally weave missing critical keywords into existing bullets (don't just list them)
- Use keywords in context that demonstrates experience, not just knowledge
- If a must-have skill is truly absent from experience, mention it as "familiar with" or "exposure to"

STEP 4 — ALIGN SKILLS SECTION:
- Reorder skill categories to match the JD's priority
- Rename categories to match the JD's language
- Lead each category with the JD's top tools
- Remove irrelevant skills that distract from the JD focus

STEP 5 — FINAL QUALITY CHECK:
- Does the resume read as a PERFECT FIT for this specific role?
- Would a recruiter see EXACTLY what the JD asks for in the first 5 seconds?
- Are the most critical ATS keywords present and used in context?
- Is the language tone consistent with the JD?

Return ONLY the complete LaTeX file, no markdown fences or explanations."""


def build_prompt(resume_latex: str, jd_text: str) -> tuple[str, str]:
    """Build system and user prompts."""
    import time
    timestamp = int(time.time() * 1000)
    
    user_prompt = f"""TASK: Transform this resume to be the PERFECT match for the job description below.

IMPORTANT: Read the JD carefully — this is a DIFFERENT role than previous ones. Analyze THIS SPECIFIC JD and transform the resume to match. Request ID: {timestamp}

ANALYSIS FIRST: Before writing, analyze the JD to understand:
- Primary role focus (building, validation, research, data engineering, etc.)
- Top 5 tools/technologies mentioned
- Must-have vs nice-to-have skills
- Tone and language style
- What a recruiter will look for in 5 seconds

THEN TRANSFORM:
- Reframe ALL experience to align with the JD's primary focus
- Use the JD's exact verbs and terminology in your bullets
- Inject missing critical ATS keywords naturally
- Restructure Technical Skills to lead with JD's priorities
- Make every bullet answer: "Why are you perfect for THIS role?"

RESUME (keep LaTeX structure, transform ALL content):

{resume_latex}

---

JOB DESCRIPTION:
{jd_text}

---

Return the complete modified LaTeX resume that reads as a PERFECT fit for this specific role."""

    return SYSTEM_PROMPT, user_prompt


def load_files(resume_path: str | Path, jd_path: str | Path) -> tuple[str, str]:
    """Load resume and job description from files."""
    resume_path = Path(resume_path)
    jd_path = Path(jd_path)

    if not resume_path.exists():
        raise FileNotFoundError(f"Resume file not found: {resume_path}")
    if not jd_path.exists():
        raise FileNotFoundError(f"Job description file not found: {jd_path}")

    resume_latex = resume_path.read_text(encoding="utf-8")
    jd_text = jd_path.read_text(encoding="utf-8")

    return resume_latex, jd_text
