#!/usr/bin/env python3
"""
Markdown to PDF converter with Mermaid diagram support

This script converts markdown files to PDF while properly rendering Mermaid diagrams.
"""

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


def find_mermaid_blocks(markdown_content: str) -> List[Tuple[str, str]]:
    """Extract mermaid blocks from markdown content.
    
    Returns a list of tuples, each containing:
    - The full match (including ```mermaid delimiters)
    - The mermaid diagram code only
    """
    pattern = r"```mermaid\n(.*?)```"
    matches = re.finditer(pattern, markdown_content, re.DOTALL)
    return [(match.group(0), match.group(1).strip()) for match in matches]


def render_mermaid_diagram(mermaid_code: str, output_path: str) -> bool:
    """Render a mermaid diagram to an image file using mmdc CLI.
    
    Args:
        mermaid_code: The mermaid diagram code
        output_path: Path to save the rendered image
        
    Returns:
        True if successful, False otherwise
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(mermaid_code)
    
    # Try local node_modules first, then global mmdc
    mmdc_path = os.path.join(os.getcwd(), 'node_modules', '.bin', 'mmdc')
    if not os.path.exists(mmdc_path):
        mmdc_path = 'mmdc'
    
    try:
        subprocess.run([
            mmdc_path,
            '-i', temp_file_path,
            '-o', output_path,
            '-b', 'transparent'
        ], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error rendering mermaid diagram: {e}")
        if hasattr(e, 'stdout'):
            print(f"stdout: {e.stdout.decode()}")
        if hasattr(e, 'stderr'):
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
    with open(input_path, 'r') as f:
        content = f.read()
    
    # Find and extract mermaid blocks
    mermaid_blocks = find_mermaid_blocks(content)
    
    if mermaid_blocks:
        # Replace mermaid blocks with image references
        base_filename = input_file.stem
        updated_content = replace_mermaid_with_images(content, mermaid_blocks, temp_dir, base_filename)
        
        # Write updated markdown to temporary file
        temp_md_path = os.path.join(temp_dir, f"{base_filename}_processed.md")
        with open(temp_md_path, 'w') as f:
            f.write(updated_content)
        
        input_for_pandoc = temp_md_path
    else:
        input_for_pandoc = input_path
    
    # Determine available PDF engine
    pdf_engine = 'xelatex'
    try:
        subprocess.run(['which', 'xelatex'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        try:
            subprocess.run(['which', 'pdflatex'], check=True, capture_output=True)
            pdf_engine = 'pdflatex'
        except subprocess.CalledProcessError:
            try:
                subprocess.run(['which', 'weasyprint'], check=True, capture_output=True)
                pdf_engine = 'weasyprint'
            except subprocess.CalledProcessError:
                try:
                    subprocess.run(['which', 'wkhtmltopdf'], check=True, capture_output=True)
                    pdf_engine = 'wkhtmltopdf'
                except subprocess.CalledProcessError:
                    print("No suitable PDF engine found (xelatex, pdflatex, weasyprint, wkhtmltopdf).")
                    return False

    print(f"Using PDF engine: {pdf_engine}")

    # Convert to PDF using pandoc
    cmd = [
        'pandoc',
        input_for_pandoc,
        '-o', output_path,
        f'--pdf-engine={pdf_engine}',
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
        '-V', 'header-includes=\\renewcommand{\\rule}[2]{\\vspace{0.5em}} \\widowpenalty=10000 \\clubpenalty=10000 \\brokenpenalty=10000'
    ]
    
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
        except subprocess.CalledProcessError:
            print(f"Required dependency not found: {dep}")
            if dep == 'npx':
                print("Please install Node.js and npm")
            elif dep == 'pandoc':
                print("Please install pandoc")
            return False
    
    # Check for mermaid-cli
    try:
        subprocess.run(
            ['mmdc', '--version'],
            check=True, capture_output=True
        )
    except subprocess.CalledProcessError:
        print("Mermaid CLI not found, installing...")
        try:
            subprocess.run(['npm', 'install', '-g', '@mermaid-js/mermaid-cli'], check=True)
        except subprocess.CalledProcessError:
            print("Failed to install @mermaid-js/mermaid-cli")
            return False
    
    return True


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert markdown files to PDF with mermaid diagram support'
    )
    parser.add_argument('input', help='Input markdown file or directory')
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
    
    # Check dependencies
    if not check_dependencies():
        print("Missing dependencies. Please install the required tools.")
        return
    
    if args.check_only:
        print("All dependencies are installed correctly.")
        return
    
    # Process input
    input_path = Path(args.input)
    if input_path.is_dir():
        process_directory(args.input, args.output, args.temp_dir)
    elif input_path.is_file():
        convert_markdown_to_pdf(args.input, args.output, args.temp_dir)
    else:
        print(f"Input path does not exist: {args.input}")


if __name__ == "__main__":
    main()