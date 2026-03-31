"""CLI entrypoint for resume tailoring."""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

from llm import OllamaProvider, PerplexityProvider
from prompt import load_files, build_prompt
from sanitize import sanitize
from compile import compile_to_pdf

load_dotenv(override=True)
def get_provider(provider_name: str, args: argparse.Namespace):
    """Create an LLM provider based on the provider name."""
    import os

    if provider_name == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = args.model or os.getenv("OLLAMA_MODEL", "llama3.2")
        return OllamaProvider(base_url=base_url, model=model)

    elif provider_name == "perplexity":
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            print("Error: PERPLEXITY_API_KEY not set in .env")
            sys.exit(1)
        model = args.model or os.getenv("PERPLEXITY_MODEL", "sonar")
        return PerplexityProvider(api_key=api_key, model=model)

    else:
        print(f"Unknown provider: {provider_name}")
        print("Available providers: ollama, perplexity")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Tailor a LaTeX resume to match a job description using LLM."
    )
    parser.add_argument(
        "--resume", "-r",
        required=True,
        help="Path to the resume LaTeX file",
    )
    parser.add_argument(
        "--jd", "-j",
        required=True,
        help="Path to the job description text file",
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Output directory for the PDF (default: current directory)",
    )
    parser.add_argument(
        "--provider", "-p",
        default="ollama",
        choices=["ollama", "perplexity"],
        help="LLM provider to use (default: ollama)",
    )
    parser.add_argument(
        "--model", "-m",
        help="Model to use (default: from .env)",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip PDF compilation (output LaTeX only)",
    )
    parser.add_argument(
        "--job-role",
        help="Job role/title (for output filename)",
    )
    parser.add_argument(
        "--company",
        help="Company name (for output filename)",
    )

    args = parser.parse_args()

    print(f"Loading resume: {args.resume}")
    print(f"Loading job description: {args.jd}")
    resume_latex, jd_text = load_files(args.resume, args.jd)
    print(f"Using provider: {args.provider}")

    provider = get_provider(args.provider, args)
    print("Calling LLM to tailor resume...")

    raw_latex = provider.generate(resume_latex, jd_text)
    print("Sanitizing output...")

    output_dir = Path(args.output)
    
    # Save raw output for debugging
    (output_dir / "debug_raw.tex").write_text(raw_latex, encoding="utf-8")
    
    clean_latex = sanitize(raw_latex)
    
    # Save clean output for debugging
    (output_dir / "debug_clean.tex").write_text(clean_latex, encoding="utf-8")

    if args.skip_compile:
        output_tex = output_dir / "resume_tailored.tex"
        output_tex.write_text(clean_latex, encoding="utf-8")
        print(f"LaTeX saved to: {output_tex}")
        return

    # Generate output filename
    if args.job_role and args.company:
        job_role_clean = args.job_role.replace(" ", "_").replace("/", "_").replace("\\", "_")
        company_clean = args.company.replace(" ", "_").replace("/", "_").replace("\\", "_")
        output_name = f"Nakshatra_{job_role_clean}_{company_clean}.pdf"
    elif args.job_role:
        job_role_clean = args.job_role.replace(" ", "_").replace("/", "_").replace("\\", "_")
        output_name = f"Nakshatra_{job_role_clean}.pdf"
    elif args.company:
        company_clean = args.company.replace(" ", "_").replace("/", "_").replace("\\", "_")
        output_name = f"Nakshatra_{company_clean}.pdf"
    else:
        output_name = "Nakshatra_Resume.pdf"

    print("Compiling to PDF...")
    pdf_path = compile_to_pdf(clean_latex, output_dir, output_name=output_name)
    print(f"PDF generated: {pdf_path}")


if __name__ == "__main__":
    main()
