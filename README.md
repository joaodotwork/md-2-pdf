# md-2-pdf

A powerful CLI tool to convert Markdown files to PDF with built-in Mermaid diagram support.

It automatically handles:
- **Mermaid Diagrams:** Renders `mermaid` code blocks into high-quality vector graphics (PDF) for lossless scaling.
- **PDF Generation:** Uses `xelatex` (or `weasyprint`/`wkhtmltopdf` as fallbacks) for professional PDF output.
- **Smart Formatting:** Includes improved defaults for readability (margins, fonts, links) and prevents bad page breaks (widows/orphans).

## Installation

### Prerequisites

1.  **Node.js & npm** (Installed automatically with the package)
2.  **Python 3** (Required for the core script)
3.  **PDF Engine** (One of the following):
    *   **Recommended:** `xelatex` (Install via [MacTeX](https://tug.org/mactex/) on macOS or `texlive` on Linux)
    *   *Fallback:* `weasyprint` (`pip install weasyprint`)

### Install via npm

```bash
npm install -g @joaodotwork/md-2-pdf
```

## Usage

### Convert a File

```bash
md-2-pdf input.md
```
This creates `input.pdf` in the same directory.

### Convert a Directory

Process all `.md` files in a folder:

```bash
md-2-pdf ./docs
```

### Options

```bash
# Specify output location
md-2-pdf input.md -o output.pdf

# Check dependencies
md-2-pdf --check-only
```

## Features

- **Mermaid Support:**
  ```mermaid
  graph TD;
      A-->B;
      A-->C;
      B-->D;
      C-->D;
  ```
  Just use standard ````mermaid blocks in your markdown. Now renders as vector graphics (PDF) instead of bitmaps for perfect clarity in your PDF exports.

- **Clean Layout:**
  - Standardized font size (11pt) and line spacing (1.2).
  - Blue clickable links.
  - Horizontal rules (`---`) rendered as vertical space instead of lines.
  - Smart page breaking rules to keep headers with content.

## License

ISC

```