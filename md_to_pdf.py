#!/usr/bin/env python3
"""
Markdown to PDF converter with Mermaid diagram support

This script converts markdown files to PDF while properly rendering Mermaid diagrams.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


# PDF engines pandoc can drive, in order of preference.
PDF_ENGINES = ('xelatex', 'pdflatex', 'weasyprint', 'wkhtmltopdf')


def find_pdf_engine() -> Optional[str]:
    """Return the first supported PDF engine found on PATH, or None.

    Returns:
        The engine name, or None if none of PDF_ENGINES is installed
    """
    for engine in PDF_ENGINES:
        try:
            subprocess.run(['which', engine], check=True, capture_output=True)
            return engine
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None


# Hiragana, katakana, CJK punctuation, kanji (incl. extension A and
# compatibility ideographs), halfwidth/fullwidth forms. Hangul is left out on
# purpose: the Harano Aji fonts below follow Adobe-Japan1 and have no Hangul,
# so switching on xeCJK for Korean would not make it render.
CJK_PATTERN = re.compile(
    '[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u31f0-\u31ff'
    '\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]'
)


def contains_cjk(text: str) -> bool:
    """Return True if text contains Japanese kana, kanji or CJK punctuation."""
    return CJK_PATTERN.search(text) is not None


def cjk_header() -> str:
    """LaTeX preamble that sets up xeCJK for Japanese text under xelatex.

    The default Latin Modern fonts have no kana or kanji, and xelatex only
    warns about missing glyphs, so without this a Japanese document
    "converts" successfully with every Japanese character silently dropped.

    Harano Aji (Mincho for serif, Gothic for sans and mono) ships with TeX
    Live, so it is passed as .otf filenames for fontspec to resolve via
    kpsewhich, the same way DejaVu Sans Mono is. Each font gets its own bold
    face, which pandoc's CJKmainfont/CJKoptions variables cannot do, since
    they share one option list between all three fonts. CJK has no italic:
    emphasised Japanese stays upright, which is the typographic convention.

    xeCJK classes some punctuation shared with Latin text as CJK: the middle
    dot and bullet (which the preamble remaps with \\newunicodechar for line
    breaking), dashes, curly quotes and the ellipsis, which would otherwise
    come out full-width in Mincho in the middle of English sentences. They
    are moved back to the Default class. Japanese
    text uses its own full-width forms (・「」), which are unaffected.
    """
    return (
        '\\usepackage{xeCJK} '
        '\\xeCJKDeclareCharClass{Default}{"00B7, "2013, "2014, "2018, "2019, "201C, "201D, "2022, "2026} '
        '\\setCJKmainfont[BoldFont=HaranoAjiMincho-Bold.otf]{HaranoAjiMincho-Regular.otf} '
        '\\setCJKsansfont[BoldFont=HaranoAjiGothic-Bold.otf]{HaranoAjiGothic-Regular.otf} '
        '\\setCJKmonofont[BoldFont=HaranoAjiGothic-Bold.otf]{HaranoAjiGothic-Regular.otf}'
    )


def find_mermaid_blocks(markdown_content: str) -> List[Tuple[str, str]]:
    """Extract mermaid blocks from markdown content.
    
    Returns a list of tuples, each containing:
    - The full match (including ```mermaid delimiters)
    - The mermaid diagram code only
    """
    pattern = r"```mermaid\n(.*?)```"
    matches = re.finditer(pattern, markdown_content, re.DOTALL)
    return [(match.group(0), match.group(1).strip()) for match in matches]


def find_mmdc() -> Optional[str]:
    """Return the mermaid-cli executable to use, or None if there is none.

    Preference order:
    1. The mermaid-cli this package depends on. npm installs it next to this
       script, in <package>/node_modules/.bin, which is not on PATH, so
       without this lookup the bundled (and version-pinned) copy was never
       used and whatever happened to be installed globally was.
    2. A node_modules/.bin/mmdc in the current directory.
    3. mmdc on PATH.
    """
    candidates = [
        Path(__file__).resolve().parent / 'node_modules' / '.bin' / 'mmdc',
        Path.cwd() / 'node_modules' / '.bin' / 'mmdc',
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which('mmdc')


_mmdc_major_cache: dict = {}


def mmdc_major_version(mmdc_path: str) -> Optional[int]:
    """Return the major version of the given mmdc, or None if unknown."""
    if mmdc_path not in _mmdc_major_cache:
        major = None
        try:
            result = subprocess.run([mmdc_path, '--version'], check=True,
                                    capture_output=True, text=True)
            match = re.search(r'(\d+)\.\d+', result.stdout)
            if match:
                major = int(match.group(1))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        _mmdc_major_cache[mmdc_path] = major
    return _mmdc_major_cache[mmdc_path]


def render_mermaid_diagram(mermaid_code: str, output_path: str) -> bool:
    """Render a mermaid diagram to an image file using mmdc CLI.
    
    Args:
        mermaid_code: The mermaid diagram code
        output_path: Path to save the rendered image
        
    Returns:
        True if successful, False otherwise
    """
    mmdc_path = find_mmdc()
    if mmdc_path is None:
        print("Error rendering mermaid diagram: mmdc (mermaid-cli) not found")
        return False

    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False,
                                     encoding='utf-8') as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(mermaid_code)

    cmd = [mmdc_path, '-i', temp_file_path, '-o', output_path,
           '-b', 'transparent']
    # PDF output has to be sized to the diagram itself. Otherwise mmdc lays
    # it onto fixed 612x792pt pages and paginates anything taller, leaving
    # page 1 blank; since \includegraphics embeds only the first page, a
    # tall diagram would silently vanish from the document. mermaid-cli 11
    # needs --pdfFit for that. 12 fits by default and rejects --pdfFit as an
    # unknown option, which failed every diagram, so pass it only before 12.
    major = mmdc_major_version(mmdc_path)
    if major is not None and major < 12:
        cmd.append('--pdfFit')

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error rendering mermaid diagram: {e}")
        if getattr(e, 'stdout', None):
            print(f"stdout: {e.stdout.decode()}")
        if getattr(e, 'stderr', None):
            print(f"stderr: {e.stderr.decode()}")
        return False
    finally:
        os.unlink(temp_file_path)


def replace_mermaid_with_images(
    markdown_content: str,
    mermaid_blocks: List[Tuple[str, str]],
    output_dir: str,
    base_filename: str
) -> str:
    """Replace mermaid code blocks with image references in the markdown.
    
    Args:
        markdown_content: The original markdown content
        mermaid_blocks: List of mermaid blocks extracted from the content
        output_dir: Directory to save rendered images
        base_filename: Base name for generated image files
        
    Returns:
        Updated markdown content with image references
    """
    updated_content = markdown_content
    
    for i, (full_match, mermaid_code) in enumerate(mermaid_blocks):
        image_filename = f"{base_filename}_diagram_{i}.pdf"
        image_path = os.path.join(output_dir, image_filename)
        
        if render_mermaid_diagram(mermaid_code, image_path):
            # Replace the mermaid block with an image reference
            image_ref = f"\n\n![Diagram {i+1}]({image_path})\n\n"
            updated_content = updated_content.replace(full_match, image_ref)
    
    return updated_content


def convert_markdown_to_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    temp_dir: Optional[str] = None
) -> bool:
    """Convert a markdown file to PDF, rendering any mermaid diagrams.
    
    Args:
        input_path: Path to the input markdown file
        output_path: Path for the output PDF file (optional)
        temp_dir: Directory to store temporary files (optional)
        
    Returns:
        True if conversion was successful, False otherwise
    """
    input_file = Path(input_path)
    
    # Determine output path if not provided
    if not output_path:
        output_path = str(input_file.with_suffix('.pdf'))
    
    # Create temp directory if not provided
    if not temp_dir:
        temp_dir = tempfile.mkdtemp()
    else:
        os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Using temporary directory: {temp_dir}")
    
    # Read the markdown content
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and extract mermaid blocks
    mermaid_blocks = find_mermaid_blocks(content)
    
    if mermaid_blocks:
        # Replace mermaid blocks with image references
        base_filename = input_file.stem
        updated_content = replace_mermaid_with_images(content, mermaid_blocks, temp_dir, base_filename)
        
        # Write updated markdown to temporary file
        temp_md_path = os.path.join(temp_dir, f"{base_filename}_processed.md")
        with open(temp_md_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        input_for_pandoc = temp_md_path
    else:
        input_for_pandoc = input_path
    
    # Determine available PDF engine
    pdf_engine = find_pdf_engine()
    if pdf_engine is None:
        print(f"No suitable PDF engine found ({', '.join(PDF_ENGINES)}).")
        return False

    print(f"Using PDF engine: {pdf_engine}")

    # Locate bundled Lua filters
    script_dir = Path(__file__).resolve().parent
    table_fit_filter = script_dir / 'filters' / 'table-fit.lua'
    code_break_filter = script_dir / 'filters' / 'code-break.lua'

    # Japanese (kana, kanji) needs CJK fonts. Only switch xeCJK on when the
    # document has CJK text, so Latin-only documents render exactly as before.
    # Its header-includes must come first: xeCJK.sty uses · literally inside
    # \csname while loading, which breaks once the \newunicodechar below has
    # made · an active character.
    cjk_args: List[str] = []
    if contains_cjk(content):
        if pdf_engine == 'xelatex':
            print("CJK text detected, enabling Japanese font support (xeCJK)")
            cjk_args = ['-V', f'header-includes={cjk_header()}']
        elif pdf_engine == 'pdflatex':
            print("Warning: CJK text detected, but pdflatex cannot typeset it. "
                  "Japanese characters will be missing; install xelatex for "
                  "CJK support.")

    # Convert to PDF using pandoc
    cmd = [
        'pandoc',
        input_for_pandoc,
        '-o', output_path,
        '--from=gfm',
        f'--pdf-engine={pdf_engine}',
        f'--lua-filter={table_fit_filter}',
        f'--lua-filter={code_break_filter}',
        '-V', 'geometry:top=0.75in',
        '-V', 'geometry:bottom=1in',
        '-V', 'geometry:left=0.75in',
        '-V', 'geometry:right=0.75in',
        '-V', 'fontsize=11pt',
        '-V', 'linestretch=1.0',
        '-V', 'parskip=6pt',
        '-V', 'colorlinks=true',
        '-V', 'linkcolor=blue',
        '-V', 'urlcolor=blue',
        *cjk_args,
        '-V', 'header-includes=\\renewcommand{\\rule}[2]{\\vspace{0.5em}} \\widowpenalty=10000 \\clubpenalty=10000 \\brokenpenalty=10000 \\setlength{\\emergencystretch}{3em} \\usepackage{newunicodechar} \\newunicodechar{·}{\\textperiodcentered\\allowbreak} \\newunicodechar{•}{\\textbullet\\allowbreak} \\usepackage{fvextra} \\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,commandchars=\\\\\\{\\}} \\DefineVerbatimEnvironment{verbatim}{Verbatim}{breaklines}',
        # Pandoc wraps every image in \pandocbounded, which scales it down to
        # fit the text block. Bounding by the full text height leaves a tall
        # diagram unable to share a page with its own heading, so it lands
        # alone on the next one and blanks the page before it. Reserving 100pt
        # lets the heading travel with the diagram. Guarded because
        # \pandocbounded only exists in pandoc 3.1.7 and later; without it,
        # images keep pandoc's own bounding.
        '-V', 'header-includes=\\makeatletter \\@ifundefined{pandocbounded}{}{'
              '\\renewcommand*\\pandocbounded[1]{\\sbox\\pandoc@box{#1}'
              '\\Gscale@div\\@tempa{\\dimexpr\\textheight-100pt\\relax}'
              '{\\dimexpr\\ht\\pandoc@box+\\dp\\pandoc@box\\relax}'
              '\\Gscale@div\\@tempb{\\linewidth}{\\wd\\pandoc@box}'
              '\\ifdim\\@tempb\\p@<\\@tempa\\p@\\let\\@tempa\\@tempb\\fi'
              '\\ifdim\\@tempa\\p@<\\p@\\scalebox{\\@tempa}{\\usebox\\pandoc@box}'
              '\\else\\usebox{\\pandoc@box}\\fi}} \\makeatother'
    ]

    # Use a Unicode-rich monospace font when the engine supports it (fontspec).
    # DejaVu Sans Mono ships with TeX Live and covers box-drawing characters
    # (│ └── ├──), so ASCII-art trees in code blocks render correctly. Pass the
    # font as a .ttf filename so fontspec resolves it via kpsewhich, which
    # works regardless of fontconfig setup or TeX Live install path.
    if pdf_engine in ('xelatex', 'lualatex'):
        cmd.extend([
            '-V', 'monofont=DejaVuSansMono.ttf',
            '-V', 'monofontoptions=BoldFont=DejaVuSansMono-Bold.ttf, ItalicFont=DejaVuSansMono-Oblique.ttf, BoldItalicFont=DejaVuSansMono-BoldOblique.ttf',
        ])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Successfully converted {input_path} to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting markdown to PDF: {e}")
        print(f"stdout: {e.stdout.decode()}")
        print(f"stderr: {e.stderr.decode()}")
        return False


def process_directory(
    input_dir: str,
    output_dir: Optional[str] = None,
    temp_dir: Optional[str] = None
) -> None:
    """Process all markdown files in a directory.
    
    Args:
        input_dir: Directory containing markdown files
        output_dir: Directory to save PDF files (optional)
        temp_dir: Directory to store temporary files (optional)
    """
    input_dir_path = Path(input_dir)
    
    # Determine output directory
    if not output_dir:
        output_dir = str(input_dir_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create temp directory if not provided
    if not temp_dir:
        temp_dir = tempfile.mkdtemp()
    else:
        os.makedirs(temp_dir, exist_ok=True)
    
    # Process each markdown file
    for md_file in input_dir_path.glob('*.md'):
        output_path = os.path.join(output_dir, f"{md_file.stem}.pdf")
        convert_markdown_to_pdf(str(md_file), output_path, temp_dir)


def check_dependencies() -> bool:
    """Check if required dependencies are installed.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    dependencies = ['npx', 'pandoc']
    
    for dep in dependencies:
        try:
            subprocess.run(['which', dep], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Required dependency not found: {dep}")
            if dep == 'npx':
                print("Please install Node.js and npm")
            elif dep == 'pandoc':
                print("Please install pandoc")
            return False

    # Check for mermaid-cli. The npm package ships it as a dependency, so
    # this normally finds the bundled copy; the global install is only a
    # fallback for running md_to_pdf.py straight from a checkout.
    mmdc_path = find_mmdc()
    if mmdc_path is None:
        print("Mermaid CLI not found, installing...")
        try:
            subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Failed to install @mermaid-js/mermaid-cli")
            print("Please install it manually: npm install -g @mermaid-js/mermaid-cli")
            return False
        mmdc_path = find_mmdc()
        if mmdc_path is None:
            print("Installed @mermaid-js/mermaid-cli, but mmdc is not on PATH")
            return False
    print(f"Found mermaid-cli: {mmdc_path} "
          f"(major version {mmdc_major_version(mmdc_path) or 'unknown'})")

    # Check for a PDF engine. Conversion picks one of these at run time, so
    # without any of them a dependency check that passed would still be
    # followed by a failed conversion.
    pdf_engine = find_pdf_engine()
    if pdf_engine is None:
        print(f"No suitable PDF engine found ({', '.join(PDF_ENGINES)}).")
        print("Please install one, e.g. xelatex (MacTeX / texlive-full) "
              "or weasyprint (pip install weasyprint)")
        return False
    print(f"Found PDF engine: {pdf_engine}")

    return True


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert markdown files to PDF with mermaid diagram support'
    )
    parser.add_argument(
        'input',
        nargs='?',
        help='Input markdown file or directory (not required with --check-only)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output PDF file (for single file) or directory (for directory input)'
    )
    parser.add_argument(
        '-t', '--temp-dir',
        help='Directory to store temporary files'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check dependencies without converting'
    )
    
    args = parser.parse_args()

    # input is optional so that --check-only can be run on its own, as the
    # README documents. Every other mode still needs it.
    if not args.check_only and args.input is None:
        parser.error("the following arguments are required: input "
                     "(omit it only with --check-only)")

    # Check dependencies
    if not check_dependencies():
        print("Missing dependencies. Please install the required tools.")
        sys.exit(1)

    if args.check_only:
        print("All dependencies are installed correctly.")
        return

    # Process input
    input_path = Path(args.input)
    if input_path.is_dir():
        process_directory(args.input, args.output, args.temp_dir)
    elif input_path.is_file():
        if not convert_markdown_to_pdf(args.input, args.output, args.temp_dir):
            sys.exit(1)
    else:
        print(f"Input path does not exist: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()