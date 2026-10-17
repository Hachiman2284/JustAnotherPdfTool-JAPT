# JAP-T

A command-line PDF toolkit (`src/pdfsuite.py`).

## Setup

Run `setupEnv.bat`. It creates a virtual environment, installs `requirements.txt`, and starts the tool.

New to the tool? Read the [User Guide](docs/USER_GUIDE.md) for step-by-step instructions on every feature.

## Running the tests

The `tests/` folder holds automated checks for every feature. You don't need them to use the
tool; they're for checking that a change hasn't broken anything.

After running `setupEnv.bat` once, double-click **`run_tests.bat`**. The first time, it installs
the test runner (`pytest`, from `requirements-dev.txt`). It ends with a summary such as
`151 passed`. Any failure names the test and shows what went wrong.

From a Command Prompt you can also run a subset, e.g. `run_tests.bat -k redact`, or run
pytest directly:

```bat
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest tests
```

Tests for OCR and PDF/A run only when Tesseract and Ghostscript are installed, and are reported
as *skipped* otherwise.

## License

The code in this repository is released under the [MIT License](LICENSE).

### Third-party dependencies

This tool uses [PyMuPDF](https://github.com/pymupdf/PyMuPDF), which is licensed under the
**GNU AGPL-3.0** (or a commercial license from Artifex). `pdf2docx` also depends on PyMuPDF.
The MIT license covers only the code in this repository. Anyone who redistributes this tool
together with PyMuPDF, or offers it as a network service, must comply with the AGPL-3.0 terms
for the combined work, or obtain a commercial PyMuPDF license.
