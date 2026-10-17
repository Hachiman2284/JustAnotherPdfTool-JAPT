# JAP-T User Guide

JAP-T (Just Another PDF Tool) is a free toolkit for everyday PDF jobs: merging, splitting, compressing, OCR, passwords, watermarks and more. Everything runs on your own computer; no files are uploaded anywhere.

This guide assumes no programming experience. If you can open a folder and double-click a file, you can use JAP-T.

## Contents

1. [What you need](#1-what-you-need)
2. [First-time setup](#2-first-time-setup)
3. [Starting the tool](#3-starting-the-tool)
4. [Using the menu](#4-using-the-menu)
5. [What each option does](#5-what-each-option-does)
6. [Page numbers and ranges](#6-page-numbers-and-ranges)
7. [Using the command line (optional)](#7-using-the-command-line-optional)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. What you need

**Required**

- **Windows 10 or 11**
- **Python 3.10 or newer** (3.13 recommended): download it from [python.org/downloads](https://www.python.org/downloads/).
  The default installer options are fine. (Ticking "Add python.exe to PATH" is optional.)

**Optional (only for some features)**

| Program | Needed for | Where to get it |
|---|---|---|
| Tesseract OCR | Option 2 (OCR), batch OCR and option 27 (PDF/A) | [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki) |
| Ghostscript | OCR and PDF/A; also gives the best results for Compress | [ghostscript.com/releases](https://ghostscript.com/releases/gsdnld.html) |
| Microsoft Word *or* LibreOffice | Option 22 (DOCX → PDF) | [libreoffice.org](https://www.libreoffice.org/download/) (free) |

You can skip these and install them later. Every other feature works without them. Install them with their normal installer; you don't need to change any Windows settings (such as PATH), because JAP-T looks in the usual install folders and wherever the installer recorded them.

---

## 2. First-time setup

You only do this once.

1. Download or copy the JAP-T folder somewhere on your computer, for example `C:\Tools\JAP-T`.
2. Open the folder and **double-click `setupEnv.bat`**.
3. A black window opens and installs everything JAP-T needs. This takes a few minutes the first time.
4. When it finishes, it shows a short **setup check** (see below), then the JAP-T menu appears. Setup is done.

The setup check lists what is ready and what is missing, for example:

```
[ OK ] Python packages
[WARN] Tesseract OCR not found. OCR (options 2 and 20) will not work. Get it from ...
```

`OK` means ready. `WARN` means one feature won't work until you install the program it names; everything else still works. `FAIL` means setup did not finish: run `setupEnv.bat` again. You can run the same check at any time with menu option **23) Check setup**, for example after installing Tesseract.

> **Tip:** If Windows shows "Windows protected your PC", click **More info → Run anyway**. This happens because the file was downloaded from the internet.

---

## 3. Starting the tool

After setup, **double-click `start.bat`** whenever you want to use JAP-T.

After each job the tool shows `Done.` or `Failed.` Press **Enter** to go back to the menu and pick the next job. When you are finished, choose **0) Exit** and press any key to close the window.

---

## 4. Using the menu

When JAP-T starts you see a numbered list:

```
PDFSuite Menu
1) PDF -> DOCX
2) OCR PDF
3) Merge PDFs
...
0) Exit
Choose [default: 0]:
```

Type the number of the job you want and press **Enter**. The tool then asks questions one at a time.

### Answering the questions

- **File paths:** type the full location of the file, for example `C:\Users\You\Documents\report.pdf`.
  The easy way: in File Explorer, hold **Shift**, right-click the file, choose **Copy as path**, then press **Ctrl + V** in the JAP-T window to paste.
  "Copy as path" adds quote marks (`"`) around the path. You can leave them in: the tool removes them for you. When you list several files separated by commas, keep the quote marks: they keep a file name that contains a comma (such as `"Invoice, March.pdf"`) in one piece.
- **Output files:** type the location and name for the new file, for example `C:\Users\You\Documents\report_small.pdf`. Missing folders are created for you. If a file with that name already exists, the tool asks `Overwrite? (y/n)`. Type `y` to replace it, or press **Enter** to type a different name. The tool will not let you use the input file's own name as the output.
- **`[default: …]`:** if a question shows a default, press **Enter** to accept it.
- **Yes/no questions:** type `y` or `n`.
- **To cancel:** press **Ctrl + C**. This stops the current job and takes you back to the menu. Pressing **Ctrl + C** at the menu itself closes the tool.

> **Tip:** Your original file is never changed. JAP-T always writes the result to a separate output file that you name.

---

## 5. What each option does

### Converting

| # | Option | What it does | You'll be asked for |
|---|---|---|---|
| 1 | **PDF → DOCX** | Turns a PDF into an editable Word document. Works best on PDFs that contain real text (not scans). | Input PDF, output `.docx` |
| 22 | **DOCX → PDF** | Turns a Word document into a PDF. Needs Microsoft Word or LibreOffice. | Input `.docx`, output PDF |
| 5 | **Images → PDF** | Combines pictures into one PDF, one picture per page. Works with JPG, PNG, TIFF, BMP, GIF and WebP. JPG, PNG and TIFF keep their full quality; all photos are turned the right way up automatically. | Image folder, output name, optional list of file names |
| 16 | **PDF → images** | Saves every page as a picture (`page_0001.png`, `page_0002.png`, …). | Input PDF, output folder, DPI, format (`png` or `jpg`) |
| 7 | **Extract text** | Saves all the text in a PDF to a `.txt` file. Press Enter at the output question to save it next to the PDF with the same name. | Input PDF, output `.txt` |
| 15 | **Extract images** | Saves every picture embedded in the PDF into a folder. | Input PDF, output folder |

**About option 5:** if you leave the file list blank, every picture in the folder is used, in name order (`img2` comes before `img10`). To choose the order yourself, type the names separated by commas: `cover.jpg, page1.png, page2.jpg`. If any listed file is missing or can't be read, nothing is created and the tool tells you which one. A multi-page TIFF becomes several pages. Transparent areas (in PNG, GIF or WebP) become white.

**About DPI (options 16 and 21):** DPI controls picture sharpness. `150` is good for screens; `300` is good for printing but makes bigger files.

### Organising pages

| # | Option | What it does | You'll be asked for |
|---|---|---|---|
| 3 | **Merge PDFs** | Joins several PDFs into one, in the order you list them. Bookmarks and form fields are kept. | Output PDF, then input PDFs separated by commas |
| 4 | **Split PDF** | Breaks a PDF into smaller files (see the modes below). | Input PDF, mode, output folder, and range or chunk size |
| 10 | **Rotate pages** | Turns pages clockwise by 90, 180 or 270 degrees. Leave pages blank to rotate all of them. | Input, output, angle, pages (optional) |
| 11 | **Delete pages** | Removes the pages you choose. You can't delete every page. | Input, output, pages to delete |
| 12 | **Reorder pages** | Puts pages in a new order. Type the old page numbers in the new order: `3,1,2` makes page 3 first. | Input, output, new order |
| 24 | **Insert pages** | Adds blank pages, or pages copied from another PDF, at the position you choose. Bookmarks keep pointing at the right pages. | Input, output, position, then either the other PDF and its pages, or how many blank pages |
| 25 | **Bookmarks** | Shows or adds bookmarks (the clickable contents list in the side panel of PDF readers). | See below |

**Insert pages:** the position is the page to insert *after*: `0` puts the new pages before page 1, `3` puts them after page 3. Blank pages get the same size as the page before them. For pages from another PDF, leave the page list blank to insert all of them.

**Bookmarks** (option 25) asks what you want to do:

- `show` lists the bookmarks, indented to show which ones sit under others.
- `add` adds one bookmark: a title and the page it opens. It is placed in page order.

**Split modes:**

- `single`: every page becomes its own file (`page_0001.pdf`, `page_0002.pdf`, …).
- `range`: copies the pages you choose into one file, `split_pages.pdf`. If your range runs past the last page, it stops at the last page.
- `chunk`: cuts the PDF into equal pieces. Chunk size `10` gives pages 1–10, 11–20, and so on (`chunk_0001.pdf`, …).

The tool asks for both a page range and a chunk size every time; it only uses the one that matches your mode, so press Enter for the other.

### Making files smaller and searchable

| # | Option | What it does |
|---|---|---|
| 6 | **Compress PDF** | Makes the file smaller, mostly by shrinking pictures. If nothing makes it smaller, you get an unchanged copy rather than a bigger file. Works best with Ghostscript installed. |
| 2 | **OCR PDF** | Reads the text in a scanned PDF so you can search, select and copy it. Needs Tesseract and Ghostscript. |
| 21 | **Convert selected pages to non-OCR** | The opposite of OCR: turns chosen pages back into plain pictures with no selectable text. Other pages are left alone. |
| 27 | **Save as PDF/A** | Converts a PDF to PDF/A, the format archives, courts and governments ask for when files must stay readable for decades. Needs Tesseract and Ghostscript. Answer `y` to also make scanned pages searchable. The result can be larger than the original, because PDF/A stores the fonts inside the file. |

**OCR questions explained:**

- **Language:** the language of the document. `eng` is English. Use `+` for mixed documents, e.g. `eng+jpn`. Each language must be installed in Tesseract.
- **Deskew:** straightens pages that were scanned at a slight angle.
- **Rotate pages:** fixes pages that were scanned sideways or upside down.
- **Remove background:** cleans up grey or speckled backgrounds.
- **Optimize (0–3):** how hard to shrink the result. `1` is a safe choice.
- **Force OCR:** redo OCR even if the PDF already has text. Use this if you see "Prior OCR/text detected".
- **Skip existing text:** only OCR pages that have no text yet.

### Passwords

| # | Option | What it does |
|---|---|---|
| 8 | **Encrypt PDF** | Adds a password. Anyone opening the file must type it. Uses strong AES-256 encryption. |
| 9 | **Decrypt PDF** | Removes the password from a PDF you have the password for. |

When the tool asks for the password, **nothing appears on screen as you type**. This is normal: it stops people nearby from reading it. Type it and press **Enter**. When you add a password (option 8), you type it twice, so a typo can't lock the file.

> **Warning:** If you forget the password of an encrypted PDF, there is no way to recover it. Keep the unencrypted original somewhere safe.

### Adding text to pages

| # | Option | What it does |
|---|---|---|
| 13 | **Add header/footer** | Writes text at the top and/or bottom of every page. |
| 14 | **Watermark** | Writes large, faint text across the middle of every page, such as `DRAFT` or `CONFIDENTIAL`. |

**Header/footer:** use `{page}` for the current page number and `{pages}` for the total. For example, the footer `Page {page} of {pages}` prints "Page 3 of 10". *Margin* is the distance from the page edge in points (72 points = 1 inch).

**Watermark:** *Rotate* is the angle in degrees (45 = diagonal). *Opacity* runs from `0` (invisible) to `1` (solid); `0.15` is a light watermark.

Both options work with non-English text such as Japanese, Chinese, Korean, Russian or Hindi. JAP-T picks a suitable font automatically.

### Removing private information

| # | Option | What it does |
|---|---|---|
| 26 | **Redact text** | Permanently removes words or phrases (names, account numbers, addresses) and puts black boxes where they were. |

Type the text to remove; separate several with `|`, for example `John Smith | 12345678`. Upper and lower case don't matter.

Unlike drawing a black box over text, redaction **deletes the text itself**, so it can't be copied, searched or recovered from the new file. Before you share the result, know these limits:

- **Scanned pages** are pictures, so their words can't be found. Run OCR (option 2) first. The tool tells you which pages had no text.
- **Hidden details**: the title, author and bookmarks are not pages, so redaction doesn't change them. The tool warns you if your text appears there; fix it with options 18 and 25.
- Always open the result and check it. If no matches are found, no file is created.

### Information and metadata

| # | Option | What it does |
|---|---|---|
| 19 | **PDF info** | Shows how many pages a PDF has and whether it is password-protected. |
| 17 | **Show metadata** | Shows hidden document details: title, author, creating program, dates. |
| 18 | **Set metadata** | Changes those details. Details you don't mention are kept. |
| 23 | **Check setup** | Shows which optional programs are installed and which features need something extra. |

**Set metadata** expects a short piece of text in this exact format (called JSON):

```
{"/Title": "Annual Report 2026", "/Author": "Jane Doe"}
```

Common keys: `/Title`, `/Author`, `/Subject`, `/Keywords`. Keep the slash, the quote marks and the curly braces.

### Batch processing

| # | Option | What it does |
|---|---|---|
| 20 | **Batch folder** | Runs one job on every PDF in a folder. |

Operations you can choose:

- `ocr` creates `name_ocr.pdf` for each file.
- `compress` creates `name_compressed.pdf` for each file.
- `extract-text` creates `name.txt` for each file.
- `watermark` creates `name_watermarked.pdf` for each file.
- `rotate` creates `name_rotated.pdf` for each file.
- `header-footer` creates `name_header_footer.pdf` for each file.

After you choose the operation, the tool asks the same questions as the single-file option (for example the watermark text, or the rotation angle) and uses your answers for every file.

> **Tip:** results are saved next to the originals unless you choose an output folder. Running the same batch again in that folder skips the first run's results (it won't create `name_rotated_rotated.pdf`), but it does replace them with new ones.

*Glob* chooses which files to include. `*.pdf` means all PDFs; `invoice*.pdf` means only PDFs whose names start with "invoice". Leave the output folder blank to save results next to the originals.

---

## 6. Page numbers and ranges

Pages are counted from **1**. Wherever the tool asks for pages, you can combine single pages and ranges with commas:

| You type | Pages selected |
|---|---|
| `5` | page 5 |
| `1-3` | pages 1, 2 and 3 |
| `1-3,6` | pages 1, 2, 3 and 6 |
| `2,9-12,16` | pages 2, 9, 10, 11, 12 and 16 |

Spaces are fine (`1 - 3, 6`). Each page counts once even if you type it twice.

---

## 7. Using the command line (optional)

You don't need this section if the menu works for you. The command line is faster for repeated jobs and lets you use the tool in scripts.

Open the JAP-T folder in File Explorer, click the address bar, type `cmd` and press Enter. Then run commands like these:

```bat
venv\Scripts\python.exe src\pdfsuite.py merge --out combined.pdf a.pdf b.pdf c.pdf
venv\Scripts\python.exe src\pdfsuite.py compress --in big.pdf --out small.pdf
venv\Scripts\python.exe src\pdfsuite.py watermark --in report.pdf --out draft.pdf --text DRAFT
venv\Scripts\python.exe src\pdfsuite.py split --in book.pdf --mode chunk --chunk-size 20 --out-dir chapters
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Scans --op ocr --lang eng
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op watermark --text DRAFT --out-dir C:\Drafts
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op header-footer --footer "Page {page} of {pages}"
```

Put paths that contain spaces in quotes: `--in "C:\My Files\report.pdf"`.

For `encrypt` and `decrypt`, leave out `--password` and the tool asks for it without showing it. If you do type `--password`, the password can be saved in your command history.

To see every command, run:

```bat
venv\Scripts\python.exe src\pdfsuite.py --help
```

and for the options of one command, add `--help` after it (e.g. `... src\pdfsuite.py ocr --help`).

| Command | Menu option |
|---|---|
| `docx` | 1. PDF → DOCX |
| `ocr` | 2. OCR PDF |
| `merge` | 3. Merge PDFs |
| `split` | 4. Split PDF |
| `images-to-pdf` (or the older `jpg-merge`) | 5. Images → PDF |
| `compress` | 6. Compress |
| `extract-text` | 7. Extract text |
| `encrypt` / `decrypt` | 8 / 9. Passwords |
| `rotate` | 10. Rotate |
| `delete-pages` | 11. Delete pages |
| `reorder` | 12. Reorder |
| `header-footer` | 13. Header/footer |
| `watermark` | 14. Watermark |
| `extract-images` | 15. Extract images |
| `to-images` | 16. PDF → images |
| `meta-show` / `meta-set` | 17 / 18. Metadata |
| `info` | 19. PDF info |
| `batch` | 20. Batch folder |
| `deocr-pages` | 21. Non-OCR pages |
| `docx-to-pdf` | 22. DOCX → PDF |
| `check` | 23. Check setup |
| `insert-pages` | 24. Insert pages |
| `bookmarks-show` / `bookmarks-add` | 25. Bookmarks |
| `redact` | 26. Redact text (repeat `--text` for each phrase) |
| `pdfa` | 27. Save as PDF/A (add `--ocr` to make scans searchable) |
| `menu` | Opens the menu |

Add `--log-level WARNING` before the command name to see only warnings and errors, or `--log-level DEBUG` to see extra detail when something goes wrong.

---

## 8. Troubleshooting

| Message or problem | What to do |
|---|---|
| `Python is not installed.` during setup | Install Python from [python.org/downloads](https://www.python.org/downloads/), then run `setupEnv.bat` again. |
| `Input PDF not found` | Check the spelling of the path. Use **Copy as path** in File Explorer to avoid typos. |
| `Missing dependency: …` | Run `setupEnv.bat` again to reinstall everything. |
| OCR fails or mentions Tesseract or Ghostscript | Install both (see [What you need](#1-what-you-need)), then close and reopen JAP-T. Option **23) Check setup** shows whether they were found. |
| `Prior OCR/text detected` | The PDF already has text. Answer `y` to **Force OCR**, or `y` to **Skip existing text**. |
| PDF/A fails with `needs Tesseract and Ghostscript` | Install both (see [What you need](#1-what-you-need)). PDF/A uses them even when it doesn't OCR anything. |
| `None of the text was found` (redact) | Check the spelling. If the page is a scan, run OCR (option 2) first, then redact the OCR result. |
| `No conversion backend available` (DOCX → PDF) | Install Microsoft Word or LibreOffice. Option **23) Check setup** shows whether either was found. |
| `File has not been decrypted` / password errors | Use option 9 to remove the password first, then run the job on the unlocked file. |
| `Incorrect password` | Passwords are case-sensitive. Check Caps Lock. |
| `page … out of bounds` | You asked for a page beyond the end of the PDF. Use option 19 to check how many pages it has. |
| Compress says it saved 0% | The PDF was already as small as it gets. Installing Ghostscript can help with scanned or photo-heavy PDFs. |
| `Setup did not finish.` | Read the message just above it, fix that problem, then run `setupEnv.bat` again. The window stays open until you press a key. |
| `JAP-T is not set up yet.` when starting | Double-click `setupEnv.bat` first. |

Still stuck? Run the same job with `--log-level DEBUG` from the command line and include the output when you ask for help.
