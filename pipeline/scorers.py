"""ATS rule-based scoring and LLM recruiter scoring."""
import re
import json
from pathlib import Path
from typing import Any


def extract_jd_keywords(jd_text: str) -> list[str]:
    """Extract key technical terms from JD for keyword matching."""
    tech_keywords = [
        "Python", "FastAPI", "Flask", "Django", "React", "Vue", "JavaScript",
        "TypeScript", "SQL", "PostgreSQL", "MongoDB", "Redis", "SQLite",
        "Docker", "Kubernetes", "CI/CD", "GitHub Actions", "Git",
        "AWS", "Azure", "GCP", "Vercel", "REST", "API", "GraphQL",
        "RAG", "LangChain", "LLM", "Generative AI", "Vector", "Embeddings",
        "STT", "TTS", "WebRTC", "Voice AI", "Conversational AI",
        "PyTorch", "TensorFlow", "Scikit-learn", "Hugging Face",
        "Cursor", "Langfuse", "Phoenix", "Observability",
        "WebSockets", "WSS", "Microservices", "Serverless",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "Data Structures", "Algorithms", "DSA",
        "HIPAA", "GDPR", "PHI", "PII", "Compliance",
        "Agile", "Scrum", "Code Review", "Testing", "pytest"
    ]
    jd_lower = jd_text.lower()
    found = [kw for kw in tech_keywords if kw.lower() in jd_lower]
    return found


def score_ats(latex: str, jd_text: str, knowledge_base: dict) -> dict[str, Any]:
    """Rule-based ATS scoring. No LLM calls.
    
    Returns: {
        "score": float (0-10),
        "details": dict,
        "weaknesses": list[str],
        "scratchpad": str
    }
    """
    checks = knowledge_base["scoring_criteria"]["ats"]["checks"]
    weaknesses = []
    details = {}
    scratchpad_lines = []
    
    # 1. Standard Headers (15%)
    required_headers = checks["standard_headers"]["required"]
    found_headers = [h for h in required_headers if h in latex]
    header_score = len(found_headers) / len(required_headers)
    missing_headers = [h for h in required_headers if h not in latex]
    if missing_headers:
        weaknesses.append(f"Missing standard headers: {', '.join(missing_headers)}")
    details["standard_headers"] = {
        "score": header_score,
        "found": found_headers,
        "missing": missing_headers
    }
    scratchpad_lines.append(f"Headers check: {len(found_headers)}/{len(required_headers)} found")
    
    # 2. Single-column (10%)
    forbidden = checks["single_column"]["forbidden_patterns"]
    has_multi_column = any(re.search(p, latex) for p in forbidden)
    column_score = 0.0 if has_multi_column else 1.0
    if has_multi_column:
        weaknesses.append("Multi-column layout detected — ATS parsers will scramble text")
    details["single_column"] = {"score": column_score, "violations": has_multi_column}
    scratchpad_lines.append(f"Single-column check: {'PASS' if column_score == 1.0 else 'FAIL'}")
    
    # 3. Keyword Density (25%)
    jd_keywords = extract_jd_keywords(jd_text)
    latex_lower = latex.lower()
    found_keywords = [kw for kw in jd_keywords if kw.lower() in latex_lower]
    keyword_score = len(found_keywords) / len(jd_keywords) if jd_keywords else 0
    missing_keywords = [kw for kw in jd_keywords if kw.lower() not in latex_lower]
    density_pct = len(found_keywords) / max(len(latex.split()) * 0.01, 1)
    if missing_keywords:
        weaknesses.append(f"Missing JD keywords: {', '.join(missing_keywords[:5])}")
    details["keyword_density"] = {
        "score": keyword_score,
        "found": len(found_keywords),
        "total": len(jd_keywords),
        "missing": missing_keywords,
        "density_pct": round(density_pct * 100, 1)
    }
    scratchpad_lines.append(f"Keyword density: {len(found_keywords)}/{len(jd_keywords)} ({round(keyword_score * 100, 1)}%)")
    
    # 4. No Tables (10%)
    # Note: tabularx is used for heading layout in the template — that's fine.
    # Only flag actual data tables: \begin{tabular}{...} and \begin{table}
    forbidden_tables = [r'\\begin\{tabular\}\{', r'\\begin\{table', r'\\begin\{minipage']
    has_tables = any(re.search(p, latex) for p in forbidden_tables)
    table_score = 0.0 if has_tables else 1.0
    if has_tables:
        weaknesses.append("Tables detected — ATS parsers treat tables as invisible objects")
    details["no_tables"] = {"score": table_score, "violations": has_tables}
    scratchpad_lines.append(f"No tables check: {'PASS' if table_score == 1.0 else 'FAIL'}")
    
    # 5. No Images (10%)
    forbidden_images = checks["no_images"]["forbidden_patterns"]
    has_images = any(re.search(p, latex) for p in forbidden_images)
    image_score = 0.0 if has_images else 1.0
    if has_images:
        weaknesses.append("Images detected — ATS parsers cannot read graphics")
    details["no_images"] = {"score": image_score, "violations": has_images}
    scratchpad_lines.append(f"No images check: {'PASS' if image_score == 1.0 else 'FAIL'}")
    
    # 6. No Header/Footer Contact (5%)
    forbidden_hf = checks["no_header_footer_contact"]["forbidden_patterns"]
    has_hf_contact = any(re.search(p, latex) for p in forbidden_hf)
    hf_score = 0.0 if has_hf_contact else 1.0
    if has_hf_contact:
        weaknesses.append("Contact info in headers/footers — parsers often skip these areas")
    details["no_header_footer_contact"] = {"score": hf_score, "violations": has_hf_contact}
    scratchpad_lines.append(f"No header/footer contact check: {'PASS' if hf_score == 1.0 else 'FAIL'}")
    
    # 7. Timeline Consistency (10%)
    dates = knowledge_base["correct_dates"]
    date_patterns = re.findall(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', latex)
    has_timeline = len(date_patterns) >= 3
    timeline_score = 1.0 if has_timeline else 0.5
    if not has_timeline:
        weaknesses.append("Timeline may be incomplete — insufficient date entries")
    details["timeline_consistency"] = {
        "score": timeline_score,
        "dates_found": len(date_patterns),
        "dates": date_patterns
    }
    scratchpad_lines.append(f"Timeline check: {len(date_patterns)} dates found")
    
    # 8. Knockout Requirements (15%)
    knockout_score = 1.0
    knockout_issues = []
    jd_lower = jd_text.lower()
    if "bachelor" in jd_lower or "degree" in jd_lower:
        has_degree = "BTech" in latex or "Bachelor" in latex or "B.S." in latex
        if not has_degree:
            knockout_score -= 0.5
            knockout_issues.append("Degree requirement may not be met")
    years_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*years?', jd_text)
    if years_match:
        min_years = int(years_match.group(1))
        max_years = int(years_match.group(2))
        if min_years > 2:
            knockout_score -= 0.3
            knockout_issues.append(f"JD requires {min_years}-{max_years} years — candidate has ~2")
    if knockout_issues:
        weaknesses.extend(knockout_issues)
    knockout_score = max(0.0, knockout_score)
    details["knockout_requirements"] = {
        "score": knockout_score,
        "issues": knockout_issues
    }
    scratchpad_lines.append(f"Knockout check: score={knockout_score}, issues={knockout_issues}")
    
    # Calculate weighted score
    weights = {
        "standard_headers": checks["standard_headers"]["weight"],
        "single_column": checks["single_column"]["weight"],
        "keyword_density": checks["keyword_density"]["weight"],
        "no_tables": checks["no_tables"]["weight"],
        "no_images": checks["no_images"]["weight"],
        "no_header_footer_contact": checks["no_header_footer_contact"]["weight"],
        "timeline_consistency": checks["timeline_consistency"]["weight"],
        "knockout_requirements": checks["knockout_requirements"]["weight"]
    }
    
    scores = {
        "standard_headers": header_score,
        "single_column": column_score,
        "keyword_density": keyword_score,
        "no_tables": table_score,
        "no_images": image_score,
        "no_header_footer_contact": hf_score,
        "timeline_consistency": timeline_score,
        "knockout_requirements": knockout_score
    }
    
    final_score = sum(scores[k] * weights[k] for k in weights) * 10
    final_score = round(min(10.0, max(0.0, final_score)), 1)
    
    return {
        "score": final_score,
        "details": details,
        "weaknesses": weaknesses,
        "scratchpad": "\n".join(scratchpad_lines)
    }


ATS_SCORING_PROMPT = """You are an ATS (Applicant Tracking System) parser evaluating a resume for: {job_role} at {company}.

Before scoring, use a <scratchpad> block to:
1. Extract all dates and mathematically calculate total months of experience
2. List the exact mandatory keywords from the JD and check if they exist in the resume
3. Check for: tables, images, non-standard headers, header/footer contact info
4. Calculate keyword density percentage

After the scratchpad, output ONLY a JSON object (no other text):
{{
  "ats_score": X,
  "missing_keywords": ["keyword1", "keyword2"],
  "issues": ["issue1", "issue2"]
}}

JD:
{jd_text}

Resume LaTeX:
{latex}"""


RECRUITER_SCORING_PROMPT = """You are a senior technical recruiter with 15+ years of experience evaluating candidates for: {job_role} at {company}.

Before scoring, use a <scratchpad> block to:
1. Analyze 3 random work experience bullets for XYZ formula compliance (Accomplished [X] as measured by [Y] through doing [Z])
2. Check for robotic patterns: "resulting in", "demonstrating ability", "similar to requirements", "Built 80% of"
3. Evaluate tone: does it sound like a real person or LLM-generated?
4. Check for over-quantification and fake metrics
5. Verify front-loaded metrics (metric in first 3 words of bullets)
6. Check for generic objectives vs professional summary
7. Check for unexplained employment gaps >6 months

After the scratchpad, output ONLY a JSON object (no other text):
{{
  "recruiter_score": X,
  "strengths": "One paragraph on what works across both ATS and human review",
  "weaknesses": "One paragraph on critical flaws, rejection triggers, and areas for improvement"
}}

Evaluation Criteria:

ATS COMPATIBILITY:
- Standard section headers (Work Experience, Education, Skills)
- Single-column layout
- Keyword density 2-3% with semantic matches
- No tables, text boxes, graphics, icons
- No vital info in headers/footers
- Meets knockout requirements (degree, years of experience)

HUMAN RECRUITER:
- XYZ formula used (Accomplished [X] as measured by [Y] through doing [Z])
- Metrics front-loaded in first 3 words of bullets
- White space strategy (clean margins, line breaks, no wall of text)
- AI-human hybrid tone (idiosyncratic project details, not generic)
- No generic objectives ("seeking a challenging role")
- No unexplained employment gaps >6 months
- No robotic phrasing
- No photos

STRICT PROTOCOL:
- Plain-text, single-column, reverse-chronological
- Semantic keywords naturally integrated into achievements
- Zero-image policy
- Balance: ATS optimization + human storytelling (not over-optimization)

JD:
{jd_text}

Resume LaTeX:
{latex}"""


SYNTHESIZER_PROMPT = """Combine the following ATS and Recruiter evaluation results into a final report.

ATS Evaluation:
{ats_output}

Recruiter Evaluation:
{recruiter_output}

Output ONLY a JSON object (no other text):
{{
  "final_strengths": "One paragraph synthesizing what works well across both ATS and human review",
  "final_weaknesses": "One paragraph synthesizing critical flaws, rejection triggers, and areas for improvement",
  "recommendation": "Good for application | Manual review needed | Not recommended"
}}"""


def build_ats_prompt(jd_text: str, latex: str, job_role: str, company: str) -> str:
    """Build ATS scoring prompt with forced CoT."""
    return ATS_SCORING_PROMPT.format(
        jd_text=jd_text, latex=latex, job_role=job_role, company=company
    )


def build_recruiter_prompt(jd_text: str, latex: str, job_role: str, company: str) -> str:
    """Build recruiter scoring prompt with forced CoT."""
    return RECRUITER_SCORING_PROMPT.format(
        jd_text=jd_text, latex=latex, job_role=job_role, company=company
    )


def build_synthesizer_prompt(ats_output: str, recruiter_output: str) -> str:
    """Build synthesizer prompt."""
    return SYNTHESIZER_PROMPT.format(
        ats_output=ats_output, recruiter_output=recruiter_output
    )


def parse_json_from_llm(text: str) -> dict:
    """Extract JSON from LLM output, handling scratchpad blocks."""
    scratchpad = ""
    scratchpad_match = re.search(r'<scratchpad>(.*?)</scratchpad>', text, re.DOTALL)
    if scratchpad_match:
        scratchpad = scratchpad_match.group(1).strip()
        text = text[scratchpad_match.end():]
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            data["_scratchpad"] = scratchpad
            return data
        except json.JSONDecodeError:
            pass
    
    return {"_scratchpad": scratchpad, "_raw": text}
