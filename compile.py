"""Compile LaTeX to PDF using pdflatex."""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


def _add_miktex_to_path():
    """Add MiKTeX to PATH if it exists."""
    miktex_paths = [
        Path(os.path.expanduser("~")) / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
        Path(r"C:\Program Files\MiKTeX\miktex\bin\x64"),
        Path(r"C:\Program Files (x86)\MiKTeX\miktex\bin"),
    ]
    
    for path in miktex_paths:
        if path.exists() and str(path) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = str(path) + ";" + os.environ.get("PATH", "")
            return True
    return False


def compile_to_pdf(latex_content: str, output_dir: Path | None = None, output_name: str = "resume_tailored.pdf") -> Path:
    """Compile LaTeX content to PDF.

    Args:
        latex_content: The LaTeX source code.
        output_dir: Directory to save the PDF. Defaults to current directory.
        output_name: Name of the output PDF file. Defaults to "resume_tailored.pdf".

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If pdflatex fails.
    """
    _add_miktex_to_path()
    
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tex_file = tmpdir / "resume.tex"

        tex_file.write_text(latex_content, encoding="utf-8")

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={tmpdir}", str(tex_file)],
            capture_output=True,
            text=True,
            cwd=str(tmpdir),
        )

        if result.returncode != 0:
            error_lines = result.stdout.split("\n")
            errors = [line for line in error_lines if "Error" in line or "!" in line]
            raise RuntimeError(
                f"pdflatex failed:\n" + "\n".join(errors[:10])
            )

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={tmpdir}", str(tex_file)],
            capture_output=True,
            text=True,
            cwd=str(tmpdir),
        )

        if result.returncode != 0:
            error_lines = result.stdout.split("\n")
            errors = [line for line in error_lines if "Error" in line or "!" in line]
            raise RuntimeError(
                f"pdflatex failed (second pass):\n" + "\n".join(errors[:10])
            )

        pdf_file = tmpdir / "resume.pdf"
        if not pdf_file.exists():
            raise RuntimeError("PDF file was not generated")

        if not output_name.endswith(".pdf"):
            output_name += ".pdf"
        
        output_pdf = output_dir / output_name
        shutil.copy2(pdf_file, output_pdf)

        return output_pdf
