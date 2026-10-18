# JAP-T: Just Another PDF Tool

A free PDF toolkit for Windows. You choose a job from a numbered menu and answer a few questions. It runs on your own computer and doesn't upload your files anywhere.

## What it can do

- Merge and split PDFs, and delete, rotate, reorder or insert pages
- Compress PDFs
- Convert between PDF and Word, turn photos (JPG, PNG and others) into a PDF, save pages as pictures, and extract the text
- Make scanned PDFs searchable (OCR)
- Add or remove passwords, permanently remove private text (redaction), and edit the title and author
- Add page numbers, headers and footers, and watermarks such as "DRAFT"
- Save as PDF/A for archiving
- Add bookmarks
- Run the same job on a whole folder of PDFs

## Getting started

You need Windows 10 or 11 and Python 3.14, which is free. Python 3.11 to 3.13 also work. The [User Guide](docs/USER_GUIDE.md#2-what-you-need) shows exactly which installer to download.

1. Click the green "Code" button on this page, then "Download ZIP".
2. Right-click the downloaded ZIP file and choose "Extract All…".
3. In the extracted folder, double-click `setupEnv.bat`. This only needs doing once and takes a few minutes.
4. After that, double-click `start.bat` whenever you want to use JAP-T.

The [User Guide](docs/USER_GUIDE.md) explains setup and every option step by step, and has a troubleshooting section. No programming knowledge is needed.

A few features need other free programs: Tesseract and Ghostscript for OCR and PDF/A, and Word or LibreOffice for Word → PDF. The setup check tells you which ones are missing. See [What you need](docs/USER_GUIDE.md#2-what-you-need).

---

## For developers

### Project layout

| Path | What it is |
|---|---|
| `src/pdfsuite.py` | The whole tool: the menu, the command line and every feature |
| `setupEnv.bat` / `start.bat` | One-time setup (finds the newest supported Python, creates `venv\` and installs `requirements.txt`) / start the menu |
| `tests/` | Automated tests |
| `run_tests.bat`, `requirements-dev.txt` | Run the tests / the test runner (`pytest`) |
| `docs/USER_GUIDE.md` | The user guide |

### Supported Python versions

Python **3.11 to 3.14**. `requirements.txt` pins exact versions, and every pinned package has a ready-made Windows build for each of these Pythons, so setup never needs a compiler. (For 3.15, several packages, including numpy, pillow and pikepdf at their pinned versions, have no Windows builds yet.) `setupEnv.bat` picks the newest supported Python through the `py` launcher (3.14, then 3.13, …) and falls back to `python` on PATH. To move an existing install to a newer Python, delete `venv\` and run `setupEnv.bat` again.

### Running the tests

The tests check every feature. You don't need them to use the tool; they're for checking that a change hasn't broken anything.

After running `setupEnv.bat` once, double-click **`run_tests.bat`**. The first time, it installs the test runner, `pytest`, from `requirements-dev.txt`. It ends with a summary such as `176 passed`. A failure names the test and shows what went wrong.

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
