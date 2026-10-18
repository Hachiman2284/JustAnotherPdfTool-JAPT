# JAP-T: Just Another PDF Tool

A free PDF toolkit for Windows. Pick a job from a simple numbered menu, answer a few questions, and you're done. Everything runs on your own computer: **your files are never uploaded anywhere.**

## What it can do

- **Combine, split and organise:** merge PDFs, split them, delete, rotate, reorder or insert pages, add bookmarks
- **Make files smaller:** compress PDFs, often to a fraction of their size
- **Convert:** PDF ↔ Word, photos (JPG, PNG, …) → PDF, PDF pages → pictures, PDF → text
- **Make scans searchable:** OCR turns scanned pages into text you can search and copy
- **Protect and clean up:** add or remove passwords, permanently black out private text (redaction), edit the title and author
- **Stamp pages:** page numbers, headers and footers, "DRAFT" watermarks
- **Archive:** save as PDF/A, the long-term format archives and courts ask for
- **Batch jobs:** run the same job on a whole folder of PDFs

## Getting started

You need **Windows 10 or 11** and **Python** (free, from [python.org/downloads](https://www.python.org/downloads/)).

1. Click the green **Code** button on this page, then **Download ZIP**.
2. Right-click the downloaded ZIP and choose **Extract All…**.
3. In the extracted folder, double-click **`setupEnv.bat`**. This is a one-time setup that takes a few minutes.
4. From then on, double-click **`start.bat`** to use JAP-T.

**New to this?** The **[User Guide](docs/USER_GUIDE.md)** walks you through everything step by step, with no programming knowledge needed. It includes a quick start, a "which option do I need?" table, and troubleshooting.

A few features need extra free programs: Tesseract and Ghostscript for OCR and PDF/A, and Word or LibreOffice for Word → PDF. Setup tells you which ones are missing; see [What you need](docs/USER_GUIDE.md#2-what-you-need).

---

## For developers

### Project layout

| Path | What it is |
|---|---|
| `src/pdfsuite.py` | The whole tool: the menu, the command line and every feature |
| `setupEnv.bat` / `start.bat` | One-time setup (creates `venv\` and installs `requirements.txt`) / start the menu |
| `tests/` | Automated tests |
| `run_tests.bat`, `requirements-dev.txt` | Run the tests / the test runner (`pytest`) |
| `docs/USER_GUIDE.md` | The user guide |

### Running the tests

The tests check every feature. You don't need them to use the tool; they're for checking that a change hasn't broken anything.

After running `setupEnv.bat` once, double-click **`run_tests.bat`**. The first time, it installs the test runner, `pytest`, from `requirements-dev.txt`. It ends with a summary such as `174 passed`. A failure names the test and shows what went wrong.

From a Command Prompt you can also run a subset, for example `run_tests.bat -k redact`, or run pytest directly:

```bat
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest tests
```

Tests that need Tesseract and Ghostscript (OCR, PDF/A) or LibreOffice run only when those are installed, and are reported as *skipped* otherwise.

## License

The code in this repository is released under the [MIT License](LICENSE).

### Third-party dependencies

This tool uses [PyMuPDF](https://github.com/pymupdf/PyMuPDF), which is licensed under the
**GNU AGPL-3.0** (or a commercial license from Artifex). `pdf2docx` also depends on PyMuPDF.
The MIT license covers only the code in this repository. Anyone who redistributes this tool
together with PyMuPDF, or offers it as a network service, must comply with the AGPL-3.0 terms
for the combined work, or obtain a commercial PyMuPDF license.
