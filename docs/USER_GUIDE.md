# JAP-T User Guide

JAP-T (Just Another PDF Tool) is a free toolkit for everyday PDF jobs: combining, splitting, shrinking, password-protecting, making scans searchable, adding watermarks and more. It runs entirely on your own Windows computer. **Your files are never uploaded anywhere.**

You don't need any programming experience. If you can open a folder and double-click a file, you can use JAP-T.

## Contents

1. [Quick start](#1-quick-start)
2. [What you need](#2-what-you-need)
3. [First-time setup](#3-first-time-setup)
4. [Using the menu](#4-using-the-menu)
5. [Which option do I need?](#5-which-option-do-i-need)
6. [What each option does](#6-what-each-option-does)
7. [Page numbers and ranges](#7-page-numbers-and-ranges)
8. [Updating or removing JAP-T](#8-updating-or-removing-jap-t)
9. [Using the command line (optional)](#9-using-the-command-line-optional)
10. [Troubleshooting](#10-troubleshooting)
11. [Words used in this guide](#11-words-used-in-this-guide)

---

## 1. Quick start

1. Install **Python 3.14** (free). See [What you need](#2-what-you-need) for exactly which file to download.
2. Download JAP-T, extract it, and **double-click `setupEnv.bat`**. This is needed once; details in [First-time setup](#3-first-time-setup).
3. From then on, **double-click `start.bat`** to open JAP-T, type the number of the job you want, and answer the questions.

### Your first job: make a PDF smaller

Here is what a complete job looks like. You type the parts after the colons; everything else is printed by JAP-T.

```
Choose [default: 0]: 6
Input PDF: "C:\Users\You\Documents\report.pdf"
Output PDF: C:\Users\You\Documents\report_small.pdf
2026-10-18 10:15:02,118 | INFO | Compressed via ghostscript/ebook: 2450118 -> 611872 (saved 1838246 bytes, 75.03%)

Done.
Press Enter to return to the menu...
```

1. At `Choose`, type `6` (Compress PDF) and press **Enter**.
2. At `Input PDF`, paste the location of your PDF (see [the easy way to type a file location](#typing-file-locations)) and press **Enter**.
3. At `Output PDF`, type a location and name for the smaller copy and press **Enter**.
4. JAP-T says `Done.` Your original `report.pdf` is unchanged, and `report_small.pdf` is the new, smaller file.

---

## 2. What you need

### Required

- **Windows 10 or 11.**
- **Python 3.14**, the free program JAP-T runs on. (Python 3.11, 3.12 and 3.13 also work.)
  1. Go to [python.org/downloads/windows](https://www.python.org/downloads/windows/).
  2. Under **Stable Releases**, find the newest **Python 3.14** (for example "Python 3.14.6") and click **Download Windows installer (64-bit)** below it.
     Don't use the big yellow button on python.org's home page: it gives the very newest Python, which JAP-T may not support yet.
  3. Open the downloaded file and click **Install Now**. The default options are fine.
  4. When it says "Setup was successful", click **Close**.

  Already have a different Python? Keep it. Just install 3.14 as well: JAP-T finds and uses 3.14 by itself.

### Optional: only for some features

Most features work without anything else. These free programs add the rest. You can install them now or later.

| Program | What it adds | Where to get it |
|---|---|---|
| **Tesseract OCR** | Making scans searchable (options 2 and 20), and PDF/A (option 27) | [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki): download the Windows installer |
| **Ghostscript** | Needed with Tesseract for OCR and PDF/A. Also makes Compress (option 6) much more effective | [ghostscript.com/releases](https://ghostscript.com/releases/gsdnld.html): choose the Windows 64-bit version |
| **Microsoft Word** *or* **LibreOffice** | Turning Word documents into PDFs (option 22) | You may already have Word. LibreOffice is free: [libreoffice.org](https://www.libreoffice.org/download/) |

Install them with their normal installer and default options. You don't need to change any Windows settings: JAP-T finds them by itself. To check what JAP-T can see, use menu option **23) Check setup**.

> **Tip:** Tesseract reads English by default. For other languages (for example Japanese or German), tick them under **Additional language data** while installing Tesseract.

---

## 3. First-time setup

You only do this once.

1. **Download JAP-T.** On the JAP-T GitHub page, click the green **Code** button, then **Download ZIP**.
2. **Extract it.** In your Downloads folder, right-click the ZIP file and choose **Extract All…**, then pick a place to keep it, for example `C:\Tools`. You'll get a folder such as `C:\Tools\JustAnotherPdfTool-JAPT-main`.
   Don't run JAP-T from inside the ZIP without extracting it first; it won't work there.
3. **Open the extracted folder and double-click `setupEnv.bat`.**
   If Windows shows **"Windows protected your PC"**, click **More info**, then **Run anyway**. Windows shows this for any file downloaded from the internet.
4. A black window opens and installs everything JAP-T needs. **The first time this takes a few minutes**, and needs an internet connection.
5. When it finishes, it shows a short **setup check** (see below), then the JAP-T menu appears. Setup is done. Type `0` and press **Enter** to close it, or go straight to your first job.

### The setup check

The setup check tells you which features are ready. It looks like this:

```
JAP-T setup check
[ OK ] Python 3.13.1
[ OK ] Python packages
[WARN] Tesseract OCR not found. OCR (options 2 and 20) and PDF/A (option 27) will not work. Get it from ...
[ OK ] Ghostscript: C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe
[ OK ] DOCX -> PDF: Microsoft Word
```

- `OK`: ready.
- `WARN`: one feature won't work until you install the program it names. **Everything else still works.**
- `FAIL`: setup didn't finish. Run `setupEnv.bat` again.

You can run this check at any time with menu option **23) Check setup**, for example after installing Tesseract.

If setup stops with **`Setup did not finish.`**, read the message just above it (for example, no internet connection), fix that, and double-click `setupEnv.bat` again. The window stays open until you press a key, so you have time to read it.

---

## 4. Using the menu

**Double-click `start.bat`** whenever you want to use JAP-T. It takes a second or two to open, then shows this list:

```
PDFSuite Menu
1) PDF -> DOCX
2) OCR PDF
3) Merge PDFs
4) Split PDF
5) Images (JPG/PNG/...) -> PDF
6) Compress PDF
7) Extract text
8) Encrypt PDF
9) Decrypt PDF
10) Rotate pages
11) Delete pages
12) Reorder pages
13) Add header/footer
14) Watermark
15) Extract images
16) PDF -> images
17) Show metadata
18) Set metadata
19) PDF info (pages/encrypted)
20) Batch folder
21) Convert selected pages to non-OCR
22) DOCX -> PDF
23) Check setup
24) Insert pages
25) Bookmarks (show/add)
26) Redact (permanently remove) text
27) Save as PDF/A (archiving)
0) Exit
Choose [default: 0]:
```

Type the number of the job you want and press **Enter**. JAP-T then asks its questions one at a time.

When the job is finished, JAP-T shows **`Done.`** or **`Failed. See the messages above.`** Press **Enter** to return to the menu for your next job. When you're finished, choose **`0`** and press any key to close the window.

### Typing file locations

Most questions ask for the location of a file, for example `C:\Users\You\Documents\report.pdf`. You don't have to type it by hand:

1. In File Explorer, find the file.
2. Hold **Shift**, right-click the file, and choose **Copy as path**.
3. Click in the JAP-T window and press **Ctrl + V** to paste, then **Enter**.

"Copy as path" puts quote marks (`"`) around the location. That's fine: leave them in.

When a question asks for **several files separated by commas** (such as merging), paste each one and separate them with commas. Keep the quote marks: they keep a file name that contains a comma, such as `"Invoice, March.pdf"`, in one piece.

### Answering the other questions

- **Output files:** type a location and name for the new file, for example `C:\Users\You\Documents\report_small.pdf`. If the folder doesn't exist yet, it's created for you.
- **Existing files:** if a file with that name already exists, JAP-T asks `Overwrite? (y/n)`. Type `y` to replace it, or press **Enter** to choose another name.
- **`[default: …]`:** if a question shows a default, press **Enter** to accept it.
- **Yes/no questions:** type `y` or `n`.
- **Changed your mind?** Press **Ctrl + C**. This cancels the current job and takes you back to the menu. Pressing **Ctrl + C** at the menu itself closes JAP-T.

> **Your originals are safe.** In the menu, JAP-T always writes the result to a new file you name. It won't let you give the output the same name as the input.

---

## 5. Which option do I need?

| I want to… | Option |
|---|---|
| Make a PDF smaller (for email, for example) | **6** Compress PDF |
| Combine several PDFs into one | **3** Merge PDFs |
| Turn photos or scans (JPG, PNG…) into one PDF | **5** Images → PDF |
| Make a scanned PDF searchable, so I can copy its text | **2** OCR PDF |
| Get some pages out as a separate PDF | **4** Split PDF (mode `range`) |
| Remove pages | **11** Delete pages |
| Turn pages that are sideways or upside down | **10** Rotate pages |
| Change the order of pages | **12** Reorder pages |
| Add a blank page, or pages from another PDF | **24** Insert pages |
| Put a password on a PDF | **8** Encrypt PDF |
| Remove a password I know | **9** Decrypt PDF |
| Add page numbers | **13** Add header/footer (use `Page {page} of {pages}`) |
| Stamp "DRAFT" or "CONFIDENTIAL" across pages | **14** Watermark |
| Black out names or account numbers for good | **26** Redact text |
| Edit a PDF in Word | **1** PDF → DOCX |
| Turn a Word document into a PDF | **22** DOCX → PDF |
| Copy all the text out of a PDF | **7** Extract text |
| Save pages as pictures | **16** PDF → images |
| Save the pictures inside a PDF | **15** Extract images |
| Do the same job to a whole folder of PDFs | **20** Batch folder |
| Store a PDF for the long term (archives, courts, government) | **27** Save as PDF/A |
| See how many pages a PDF has | **19** PDF info |
| See or change the title and author stored in a PDF | **17** / **18** Metadata |
| Add bookmarks (the clickable contents in the side panel) | **25** Bookmarks |
| Check which features are ready | **23** Check setup |

---

## 6. What each option does

### Converting

| # | Option | What it does | You'll be asked for |
|---|---|---|---|
| 1 | **PDF → DOCX** | Turns a PDF into an editable Word document. Works best on PDFs that contain real text, not scans. | Input PDF, output `.docx` |
| 22 | **DOCX → PDF** | Turns a Word document into a PDF. Needs Microsoft Word or LibreOffice. | Input `.docx`, output PDF |
| 5 | **Images → PDF** | Combines pictures into one PDF, one picture per page. Works with JPG, PNG, TIFF, BMP, GIF and WebP. JPG, PNG and TIFF keep their full quality, and photos are turned the right way up automatically. | Image folder, output name, optional list of file names |
| 16 | **PDF → images** | Saves every page as a picture (`page_0001.png`, `page_0002.png`, …). | Input PDF, output folder, DPI, format (`png` or `jpg`) |
| 7 | **Extract text** | Saves all the text in a PDF to a `.txt` file. Press **Enter** at the output question to save it next to the PDF with the same name. | Input PDF, output `.txt` |
| 15 | **Extract images** | Saves every picture inside the PDF into a folder. | Input PDF, output folder |

**About option 5:**
- Leave the file list blank to use every picture in the folder, in name order (`img2` comes before `img10`).
- To choose the order yourself, type the names separated by commas: `cover.jpg, page1.png, page2.jpg`.
- If you type just a name for the output (like the default `merged_output.pdf`), it's saved in the image folder.
- If any listed file is missing or can't be read, nothing is created, and JAP-T tells you which file.
- A multi-page TIFF becomes several pages. Transparent areas (in PNG, GIF or WebP) become white.

**About option 22:** if you have Microsoft Word, JAP-T uses it. Otherwise it uses LibreOffice. For LibreOffice, JAP-T keeps its own separate LibreOffice settings, so it doesn't disturb a LibreOffice window you have open, and it never checks for or installs LibreOffice updates. The very first conversion can take a little longer while those settings are created.

**About DPI (options 16 and 21):** DPI controls picture sharpness. `150` is good for screens; `300` is good for printing but makes bigger files.

### Organising pages

| # | Option | What it does | You'll be asked for |
|---|---|---|---|
| 3 | **Merge PDFs** | Joins several PDFs into one, in the order you list them. Bookmarks and form fields are kept. | Input PDFs separated by commas, then the output PDF |
| 4 | **Split PDF** | Breaks a PDF into smaller files (see the modes below). | Input PDF, mode, output folder, file name prefix, and page range or chunk size |
| 10 | **Rotate pages** | Turns pages clockwise by 90, 180 or 270 degrees. Leave the pages blank to rotate all of them. | Input, output, angle, pages (optional) |
| 11 | **Delete pages** | Removes the pages you choose. You can't delete every page. | Input, output, pages to delete |
| 12 | **Reorder pages** | Puts pages in a new order. Type the old page numbers in the new order: `3,1,2` makes page 3 first. | Input, output, new order |
| 24 | **Insert pages** | Adds blank pages, or pages copied from another PDF, where you choose. Bookmarks keep pointing at the right pages. | Input, output, position, then either the other PDF and its pages, or how many blank pages |
| 25 | **Bookmarks** | Shows or adds bookmarks: the clickable contents list in the side panel of PDF readers. | See below |

**Split modes:**

- `single`: every page becomes its own file (`page_0001.pdf`, `page_0002.pdf`, …).
- `range`: copies the pages you choose into one file, `split_pages.pdf`. If your range runs past the last page, it stops at the last page.
- `chunk`: cuts the PDF into equal pieces. Chunk size `10` gives pages 1–10, 11–20, and so on (`chunk_0001.pdf`, …).

JAP-T asks for both a page range and a chunk size every time. It only uses the one that matches your mode, so just press **Enter** for the other.

**Insert pages:** the position is the page to insert *after*. `0` puts the new pages before page 1; `3` puts them after page 3. Blank pages get the same size as the page before them. When taking pages from another PDF, leave the page list blank to insert all of them.

**Bookmarks** (option 25) first asks what you want to do:

- `show` lists the bookmarks, indented to show which ones sit under others.
- `add` adds one bookmark: a title and the page it opens. It's placed in page order.

### Making files smaller and searchable

| # | Option | What it does |
|---|---|---|
| 6 | **Compress PDF** | Makes the file smaller, mostly by shrinking pictures. If nothing makes it smaller, you get an unchanged copy rather than a bigger file. Works much better with Ghostscript installed. |
| 2 | **OCR PDF** | Reads the text in a scanned PDF so you can search, select and copy it. Needs Tesseract and Ghostscript. |
| 21 | **Convert selected pages to non-OCR** | The opposite of OCR: turns chosen pages back into plain pictures with no selectable text. Other pages are left alone. |
| 27 | **Save as PDF/A** | Converts a PDF to PDF/A, the format archives, courts and governments ask for when files must stay readable for decades. Needs Tesseract and Ghostscript. Answer `y` to also make scanned pages searchable. The result can be larger than the original, because PDF/A stores the fonts inside the file. |

**OCR questions explained** (press **Enter** to accept the default for any of them):

- **Language:** the language of the document. `eng` is English. For mixed documents, join languages with `+`, for example `eng+jpn`. Each language must be installed in Tesseract (see the [tip](#optional-only-for-some-features)).
- **Deskew:** straightens pages that were scanned at a slight angle.
- **Rotate pages:** fixes pages that were scanned sideways or upside down.
- **Remove background:** cleans up grey or speckled backgrounds.
- **Optimize (0–3):** how hard to shrink the result. `1` is a safe choice.
- **Force OCR:** redo OCR even if the PDF already has text. Use this if you see "Prior OCR/text detected".
- **Skip existing text:** only OCR the pages that have no text yet.

### Passwords

| # | Option | What it does |
|---|---|---|
| 8 | **Encrypt PDF** | Adds a password. Anyone opening the file must type it. Uses strong AES-256 encryption. |
| 9 | **Decrypt PDF** | Removes the password from a PDF you know the password for. |

When JAP-T asks for the password, **nothing appears on screen as you type**. That's normal: it stops people nearby from seeing it. Type it and press **Enter**. When adding a password (option 8), you type it twice, so a typo can't lock you out.

> **Warning:** if you forget the password of an encrypted PDF, there is no way to get it back. Keep the unencrypted original somewhere safe.

### Adding text to pages

| # | Option | What it does |
|---|---|---|
| 13 | **Add header/footer** | Writes text at the top and/or bottom of every page. |
| 14 | **Watermark** | Writes large, faint text across the middle of every page, such as `DRAFT` or `CONFIDENTIAL`. |

**Header/footer:** use `{page}` for the page number and `{pages}` for the total. For example, the footer `Page {page} of {pages}` prints "Page 3 of 10" on page 3. *Margin* is the distance from the edge of the page in points (72 points = 1 inch).

**Watermark:** *Rotate* is the angle in degrees (`45` is diagonal; decimals such as `22.5` work too). *Opacity* goes from `0` (invisible) to `1` (solid); `0.15` gives a light watermark.

Both options work with non-English text such as Japanese, Chinese, Korean, Russian or Hindi. JAP-T picks a suitable font automatically.

### Removing private information

| # | Option | What it does |
|---|---|---|
| 26 | **Redact text** | Permanently removes words or phrases (names, account numbers, addresses) and puts black boxes where they were. |

Type the text to remove. To remove several things, separate them with `|`, for example `John Smith | 12345678`. Upper and lower case don't matter.

Unlike drawing a black box over text, redaction **deletes the text itself**, so it can't be copied, searched or recovered from the new file. Before you share the result, know the limits:

- **Scanned pages** are pictures, so their words can't be found. Run OCR (option 2) first, then redact the OCR result. JAP-T tells you which pages had no text.
- **Hidden details:** the title, author and bookmarks aren't part of the pages, so redaction doesn't change them. JAP-T warns you if your text appears there; fix them with options 18 and 25.
- If none of the text is found, no file is created.
- Always open the result and check it before sharing it.

### Information and metadata

| # | Option | What it does |
|---|---|---|
| 19 | **PDF info** | Shows how many pages a PDF has and whether it's password-protected. |
| 17 | **Show metadata** | Shows the hidden document details: title, author, the program that created it, dates. |
| 18 | **Set metadata** | Changes those details. Details you don't mention are kept. |
| 23 | **Check setup** | Shows which optional programs are installed and which features need something extra. |

**Set metadata** expects the details in this exact format (called JSON):

```
{"/Title": "Annual Report 2026", "/Author": "Jane Doe"}
```

Common keys are `/Title`, `/Author`, `/Subject` and `/Keywords`. Keep the slashes, the quote marks and the curly braces exactly as shown.

### Batch processing

| # | Option | What it does |
|---|---|---|
| 20 | **Batch folder** | Runs one job on every PDF in a folder. |

You choose one of these operations. Each creates a new file per PDF:

| Operation | Creates |
|---|---|
| `ocr` | `name_ocr.pdf` |
| `compress` | `name_compressed.pdf` |
| `extract-text` | `name.txt` |
| `watermark` | `name_watermarked.pdf` |
| `rotate` | `name_rotated.pdf` |
| `header-footer` | `name_header_footer.pdf` |

After you choose, JAP-T asks the same questions as the single-file option (for example the watermark text, or the rotation angle) and uses your answers for every file.

- **Glob** chooses which files to include. Press **Enter** for `*.pdf` (all PDFs); `invoice*.pdf` means only PDFs whose names start with "invoice".
- **Output folder:** leave it blank to save the results next to the originals.
- **Running the same batch again** in the same folder skips the first run's results (it won't create `name_rotated_rotated.pdf`), but it replaces them with new ones.
- If some files fail, JAP-T names them and shows `Failed.`, even though the others were done.

---

## 7. Page numbers and ranges

Pages are counted from **1**. Wherever JAP-T asks for pages, you can mix single pages and ranges, separated by commas:

| You type | Pages selected |
|---|---|
| `5` | page 5 |
| `1-3` | pages 1, 2 and 3 |
| `1-3,6` | pages 1, 2, 3 and 6 |
| `2,9-12,16` | pages 2, 9, 10, 11, 12 and 16 |

Spaces are fine (`1 - 3, 6`). A page counts once even if you type it twice. Not sure how many pages a PDF has? Use option **19**.

---

## 8. Updating or removing JAP-T

### Updating to a newer version

1. Download and extract the new version, as in [First-time setup](#3-first-time-setup), into a **new** folder.
2. Double-click `setupEnv.bat` in the new folder.
3. When it works, you can delete the old folder.

Your PDFs aren't stored inside the JAP-T folder, so updating never touches them.

> If you downloaded JAP-T with Git instead of a ZIP: run `git pull` in the JAP-T folder, then double-click `setupEnv.bat`.

### Removing JAP-T

1. Delete the JAP-T folder.
2. Optional: delete JAP-T's LibreOffice settings. In File Explorer, click the address bar, type `%LOCALAPPDATA%` and press **Enter**, then delete the `JAP-T` folder there. It exists only if you've converted Word documents with LibreOffice.

Python, Tesseract, Ghostscript and LibreOffice are separate programs. If you no longer need them, remove them like any other program, in Windows **Settings → Apps**.

---

## 9. Using the command line (optional)

You don't need this section if the menu works for you. The command line is faster for repeated jobs and lets you use JAP-T in scripts.

Open the JAP-T folder in File Explorer, click the address bar, type `cmd` and press **Enter**. A Command Prompt opens in that folder. Then run commands like these:

```bat
venv\Scripts\python.exe src\pdfsuite.py merge --out combined.pdf a.pdf b.pdf c.pdf
venv\Scripts\python.exe src\pdfsuite.py compress --in big.pdf --out small.pdf
venv\Scripts\python.exe src\pdfsuite.py watermark --in report.pdf --out draft.pdf --text DRAFT
venv\Scripts\python.exe src\pdfsuite.py split --in book.pdf --mode chunk --chunk-size 20 --out-dir chapters
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Scans --op ocr --lang eng
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op watermark --text DRAFT --out-dir C:\Drafts
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op header-footer --footer "Page {page} of {pages}"
```

- Put paths that contain spaces in quotes: `--in "C:\My Files\report.pdf"`.
- Unlike the menu, the command line **does** let `--out` be the same file as `--in`, and overwrites it without asking.
- For `encrypt` and `decrypt`, leave out `--password` and JAP-T asks for it without showing it. If you type `--password`, the password can end up saved in your command history.

To see every command, run:

```bat
venv\Scripts\python.exe src\pdfsuite.py --help
```

For the options of one command, add `--help` after it, for example `venv\Scripts\python.exe src\pdfsuite.py ocr --help`.

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

## 10. Troubleshooting

| Message or problem | What to do |
|---|---|
| "Windows protected your PC" | Click **More info**, then **Run anyway**. Windows shows this for files downloaded from the internet. |
| `Python is not installed.` during setup | Install Python 3.14 (see [What you need](#2-what-you-need)), then run `setupEnv.bat` again. |
| `Found Python 3.x, but JAP-T needs Python 3.11, 3.12, 3.13 or 3.14.` | Your Python is too new or too old. Install Python 3.14 as well (see [What you need](#2-what-you-need)); you can keep the other one. Then run `setupEnv.bat` again. |
| `Setup did not finish.` | Read the message just above it, fix that problem (often: no internet connection), then run `setupEnv.bat` again. |
| `JAP-T is not set up yet.` when starting | Double-click `setupEnv.bat` first. |
| `Missing Python package: …` | Setup didn't finish. Run `setupEnv.bat` again. |
| `Input PDF not found` | The location is mistyped. Use **Copy as path** in File Explorer (see [Typing file locations](#typing-file-locations)). |
| OCR fails, or mentions Tesseract or Ghostscript | Install both (see [What you need](#2-what-you-need)), then close and reopen JAP-T. Option **23) Check setup** shows whether they were found. |
| `Prior OCR/text detected` | The PDF already has text. Answer `y` to **Force OCR**, or `y` to **Skip existing text**. |
| PDF/A fails with `needs Tesseract and Ghostscript` | Install both (see [What you need](#2-what-you-need)). PDF/A uses them even when it doesn't OCR anything. |
| `None of the text was found` (redact) | Check the spelling. If the page is a scan, run OCR (option 2) first, then redact the OCR result. |
| `No conversion backend available` (DOCX → PDF) | Install Microsoft Word or LibreOffice. Option **23) Check setup** shows whether either was found. |
| `File has not been decrypted`, or other password errors | The PDF is password-protected. Use option 9 to remove the password first, then run the job on the unlocked file. |
| `Incorrect password` | Passwords are case-sensitive. Check Caps Lock, and remember that nothing appears on screen while you type. |
| `page … out of bounds` | You asked for a page beyond the end of the PDF. Use option 19 to check how many pages it has. |
| Compress saved 0% | The PDF was already as small as it gets. Installing Ghostscript helps with scanned or photo-heavy PDFs. |
| `Failed.` after a batch | Some files failed. JAP-T lists them above `Failed.`; the other files were done. |

Still stuck? Run the same job from the command line with `--log-level DEBUG` (see [section 9](#9-using-the-command-line-optional)), and include the output when you ask for help.

---

## 11. Words used in this guide

| Word | Meaning |
|---|---|
| **OCR** | "Optical character recognition": reading the words in a picture of a page (a scan), so you can search and copy them. |
| **Scan / scanned PDF** | A PDF whose pages are pictures, for example from a scanner or phone camera. You can't select its text until it has been OCRed. |
| **Redact** | Remove information for good, so it can't be recovered. |
| **PDF/A** | A version of PDF designed to stay readable for decades. Archives, courts and governments often require it. |
| **Metadata** | Hidden details stored in a file, such as its title and author. |
| **DPI** | "Dots per inch": how sharp a picture is. Higher means sharper and larger files. |
| **Watermark** | Faint text printed across a page, such as "DRAFT". |
| **Encrypt / decrypt** | Add / remove a password. |
| **Glob** | A pattern that selects files by name. `*` means "anything", so `*.pdf` means every PDF. |
| **Command Prompt** | A window where you type commands instead of clicking. Only needed for the optional [command line](#9-using-the-command-line-optional). |
