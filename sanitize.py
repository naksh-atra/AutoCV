"""Sanitize LLM output to valid LaTeX."""
import re


def sanitize(raw_output: str) -> str:
    """Clean LLM output to produce valid LaTeX.

    Removes markdown fences, fixes common LLM LaTeX mistakes,
    and ensures proper document structure.
    """
    latex = raw_output.strip()

    latex = re.sub(r"^```latex\s*\n?", "", latex, flags=re.MULTILINE)
    latex = re.sub(r"^```\s*\n?", "", latex, flags=re.MULTILINE)
    latex = re.sub(r"\n?```$", "", latex)

    if "\\documentclass" not in latex:
        raise ValueError("No \\documentclass found - output is not valid LaTeX")

    # Strip everything before \documentclass (LLM analysis notes, etc.)
    doc_class_index = latex.find("\\documentclass")
    latex = latex[doc_class_index:]

    if "\\begin{document}" not in latex:
        raise ValueError("No \\begin{document} found - output is not valid LaTeX")

    if "\\end{document}" not in latex:
        latex = latex.rstrip() + "\n\\end{document}\n"
    else:
        # Remove anything after \end{document} (LLM analysis notes, etc.)
        end_doc_index = latex.find("\\end{document}")
        latex = latex[:end_doc_index + len("\\end{document}")]

    latex = re.sub(r'\\textbf\{\\textbf\{([^}]+)\}\}', r'\\textbf{\1}', latex)
    latex = re.sub(r'\\textit\{\\textit\{([^}]+)\}\}', r'\\textit{\1}', latex)

    latex = re.sub(r'\\textbf\{\s*\}', '', latex)
    latex = re.sub(r'\\textit\{\s*\}', '', latex)

    latex = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', latex)
    latex = re.sub(r'\*([^*]+)\*', r'\\textit{\1}', latex)

    # Fix common LLM LaTeX errors
    # Fix \begin{tabularx}{\textwidth}{\textwidth}{X r} -> \begin{tabularx}{\textwidth}{X r}
    latex = re.sub(r'\\begin\{tabularx\}\{\\textwidth\}\{\\textwidth\}', r'\\begin{tabularx}{\\textwidth}', latex)
    # Fix \begin{tabularx}{\textwidth}{\textwidth r} -> \begin{tabularx}{\textwidth}{X r}
    latex = re.sub(r'\\begin\{tabularx\}\{\\textwidth\}\{\\textwidth r\}', r'\\begin{tabularx}{\\textwidth}{X r}', latex)
    # Fix \begin{tabularx}{\textwidth}{\textwidth l} -> \begin{tabularx}{\textwidth}{X l}
    latex = re.sub(r'\\begin\{tabularx\}\{\\textwidth\}\{\\textwidth l\}', r'\\begin{tabularx}{\\textwidth}{X l}', latex)

    latex = re.sub(r'[^\x00-\x7F]+', '', latex)

    # Remove hidden text (white color text or invisible phrases)
    latex = re.sub(r'\\vfill\s*\n?\\color\{white\}[^}]*\}', '', latex)
    latex = re.sub(r'\\color\{white\}[^}]*\}', '', latex)

    return latex.strip()
