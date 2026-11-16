#!/usr/bin/env python3
"""End-to-end smoke test: convert test/fixture.md and check the PDF.

Checks the things that have broken silently before, where the conversion
still exited 0:
- every mermaid diagram rendered (mermaid-cli 12 rejected --pdfFit, and the
  diagram was left as a code block), including a tall one (1.4.1);
- Japanese text is present in the PDF rather than dropped (1.5.0).

Needs pandoc, xelatex (with xeCJK and Harano Aji), mermaid-cli via
`npm ci`, and poppler's pdftotext.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / 'test' / 'fixture.md'

EXPECTED_TEXT = [
    'SmokeNodeAlpha',   # top of the tall diagram
    'SmokeNodeOmega',   # bottom of it: the whole diagram made it in
    'ぷらんたす',        # hiragana
    'プランタス',        # katakana
    '植物',              # kanji
    '日本語の見出し',     # CJK in a heading
    'コード',            # CJK in a code block
]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out_pdf = Path(tmp) / 'fixture.pdf'
        result = subprocess.run(
            [sys.executable, str(ROOT / 'md_to_pdf.py'), str(FIXTURE),
             '-o', str(out_pdf), '-t', str(Path(tmp) / 'work')],
            capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr, file=sys.stderr)

        failures = []
        if result.returncode != 0:
            failures.append(f'md_to_pdf.py exited {result.returncode}')
        if 'Error rendering mermaid diagram' in result.stdout:
            failures.append('a mermaid diagram failed to render')
        if not out_pdf.exists():
            failures.append('no PDF was produced')
        else:
            text = subprocess.run(['pdftotext', str(out_pdf), '-'],
                                  capture_output=True, text=True,
                                  check=True).stdout
            failures += [f'missing from PDF text: {s!r}'
                         for s in EXPECTED_TEXT if s not in text]

    if failures:
        print('FAIL\n  ' + '\n  '.join(failures))
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
