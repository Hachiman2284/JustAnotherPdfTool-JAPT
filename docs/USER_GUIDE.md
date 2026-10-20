# JAP-T User Guide

JAP-T (Just Another PDF Tool) is a free program for common PDF jobs, such as joining and splitting files, making them smaller, adding passwords, making scans searchable and adding watermarks. It runs on your own Windows computer and does not upload your files anywhere.

No programming knowledge is needed. You start JAP-T by double-clicking a file, pick a job from a numbered list and answer a few questions.

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

1. Install Python 3.14, which is free. [What you need](#2-what-you-need) says which file to download.
2. Download JAP-T, extract it and double-click `setupEnv.bat`. You only do this once. [First-time setup](#3-first-time-setup) has the details.
3. After that, double-click `start.bat` whenever you want to use JAP-T.

### Example: making a PDF smaller

This is a complete job. You type the parts after each colon, and JAP-T prints the rest.

```
Choose [default: 0]: 6
Input PDF: "C:\Users\You\Documents\report.pdf"
Output PDF: C:\Users\You\Documents\report_small.pdf
2026-10-18 10:15:02,118 | INFO | Compressed via ghostscript/ebook: 2450118 -> 611872 (saved 1838246 bytes, 75.03%)

Done.
Press Enter to return to the menu...
```

1. At `Choose`, type `6` (Compress PDF) and press Enter.
2. At `Input PDF`, paste the location of your PDF and press Enter. [Typing file locations](#typing-file-locations) explains how to copy it.
3. At `Output PDF`, type a location and name for the smaller copy and press Enter.
4. JAP-T prints `Done.` The original `report.pdf` is unchanged, and `report_small.pdf` is the new, smaller copy.

---

## 2. What you need

### Required

You need Windows 10 or 11 and Python 3.14. Python is the free program JAP-T runs on. Python 3.11, 3.12 and 3.13 also work.

To install Python:

1. Go to [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. Under "Stable Releases", find the newest Python 3.14 (for example "Python 3.14.6") and click "Download Windows installer (64-bit)" underneath it.
3. Open the downloaded file and click "Install Now". The default options are fine.
4. When the installer says "Setup was successful", click "Close".

Avoid the large yellow download button on python.org's home page. It always offers the newest Python, and JAP-T may not support that version yet.

If you already have another version of Python, you can keep it. Install 3.14 next to it, and setup will choose 3.14.

### Optional

Most features work without anything else. A few need one of these free programs, which you can install now or later.

| Program | Needed for | Where to get it |
|---|---|---|
| Tesseract OCR | Making scans searchable (options 2 and 20) and PDF/A (option 27) | [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki). Download the Windows installer. |
| Ghostscript | OCR and PDF/A, together with Tesseract. It also makes Compress (option 6) much more effective. | [ghostscript.com/releases](https://ghostscript.com/releases/gsdnld.html). Choose the Windows 64-bit version. |
| Microsoft Word or LibreOffice | Turning Word documents into PDFs (option 22) | You may already have Word. LibreOffice is free from [libreoffice.org](https://www.libreoffice.org/download/). |

Install them with their normal installers and default options. JAP-T finds them without any changes to Windows settings. Menu option 23 (Check setup) shows which ones it has found.

Tesseract only reads English unless you add more languages. To read other languages, such as Japanese or German, tick them under "Additional language data" while installing Tesseract.

---

## 3. First-time setup

You only need to do this once.

1. On the JAP-T GitHub page, click the "Code" button above the list of files, then "Download ZIP".
2. In your Downloads folder, right-click the ZIP file and choose "Extract All…". Pick a place to keep JAP-T, for example `C:\Tools`. This creates a folder such as `C:\Tools\JustAnotherPdfTool-JAPT-main`.
   JAP-T does not work from inside the ZIP file, so make sure you extract it first.
3. Open the extracted folder and double-click `setupEnv.bat`.
   Windows may show a "Windows protected your PC" message, because the file came from the internet. Click "More info", then "Run anyway".
4. A black window opens and installs what JAP-T needs. This takes a few minutes the first time and needs an internet connection.
5. When it finishes, it prints a short setup check (described below) and then opens the JAP-T menu. Type `0` and press Enter to close it, or carry on with your first job.

### The setup check

The setup check lists which features are ready. It looks something like this:

```
JAP-T setup check
[ OK ] Python 3.14.6
[ OK ] Python packages
[WARN] Tesseract OCR not found. OCR (options 2 and 20) and PDF/A (option 27) will not work. Get it from ...
[ OK ] Ghostscript 10.08.0: C:\Program Files\gs\gs10.08.0\bin\gswin64c.exe
[ OK ] DOCX -> PDF: Microsoft Word
```

- `OK` means ready.
- `WARN` means one feature won't work until you install the program it names. The rest of JAP-T works normally.
  A warning that Ghostscript is out of date means your version has known security problems. Everything still works, but install the latest version from the Ghostscript website. It replaces the old one, or you can uninstall the old one afterwards from Settings → Apps.
- `FAIL` means setup did not finish. Run `setupEnv.bat` again.

You can run the same check later with menu option 23, for example after installing Tesseract.

If setup stops with `Setup did not finish.`, the line just above it says why, for example that there is no internet connection. Fix that and run `setupEnv.bat` again. The window stays open until you press a key.

---

## 4. Using the menu

Double-click `start.bat` to open JAP-T. After a second or two it shows this list:

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

Type the number of a job and press Enter. JAP-T then asks its questions one at a time.

At the end of each job it prints `Done.` or `Failed. See the messages above.` Press Enter to go back to the menu. To close JAP-T, choose `0` and then press any key.

### Typing file locations

Most questions ask where a file is, for example `C:\Users\You\Documents\report.pdf`. Instead of typing this yourself, you can copy it:

1. Find the file in File Explorer.
2. Hold Shift, right-click the file and choose "Copy as path".
3. Click in the JAP-T window, press Ctrl+V to paste, then press Enter.

"Copy as path" adds quote marks (`"`) around the location. You can leave them in.

Some questions, such as the one for merging, ask for several files separated by commas. Paste each file and put a comma between them. Keep the quote marks here as well. They make sure a file name that contains a comma, such as `"Invoice, March.pdf"`, is read as one file.

### Other questions

- Output files: type a location and name for the new file, for example `C:\Users\You\Documents\report_small.pdf`. If the folder doesn't exist yet, JAP-T creates it.
- If a file with that name already exists, JAP-T asks `Overwrite? (y/n)`. Type `y` to replace it, or press Enter to choose a different name.
- When a question shows `[default: …]`, pressing Enter accepts the value shown.
- For yes/no questions, type `y` or `n`.
- To cancel a job, press Ctrl+C. JAP-T stops the job and returns to the menu. Pressing Ctrl+C at the menu closes JAP-T.

The menu never changes your original file. It always saves the result as a new file, and it will not accept the original file's name as the output name.

---

## 5. Which option do I need?

| I want to… | Option |
|---|---|
| Make a PDF smaller, for example to send by email | 6 Compress PDF |
| Combine several PDFs into one | 3 Merge PDFs |
| Turn photos or scans (JPG, PNG…) into one PDF | 5 Images → PDF |
| Make a scanned PDF searchable, so I can copy its text | 2 OCR PDF |
| Save some of the pages as a separate PDF | 4 Split PDF (mode `range`) |
| Remove pages | 11 Delete pages |
| Turn pages that are sideways or upside down | 10 Rotate pages |
| Change the order of pages | 12 Reorder pages |
| Add a blank page, or pages from another PDF | 24 Insert pages |
| Put a password on a PDF | 8 Encrypt PDF |
| Remove a password I know | 9 Decrypt PDF |
| Add page numbers | 13 Add header/footer (use `Page {page} of {pages}`) |
| Print "DRAFT" or "CONFIDENTIAL" across the pages | 14 Watermark |
| Permanently remove names or account numbers | 26 Redact text |
| Edit a PDF in Word | 1 PDF → DOCX |
| Turn a Word document into a PDF | 22 DOCX → PDF |
| Copy all the text out of a PDF | 7 Extract text |
| Save the pages as pictures | 16 PDF → images |
| Save the pictures that are inside a PDF | 15 Extract images |
| Do the same job to a whole folder of PDFs | 20 Batch folder |
| Keep a PDF in an archive format (often required by courts or government offices) | 27 Save as PDF/A |
| Find out how many pages a PDF has | 19 PDF info |
| See or change the title and author stored in a PDF | 17 / 18 Metadata |
| Add bookmarks (the list of links in a PDF reader's side panel) | 25 Bookmarks |
| Check which features are ready | 23 Check setup |

---

## 6. What each option does

### Converting

| # | Option | What it does | Questions |
|---|---|---|---|
| 1 | PDF → DOCX | Turns a PDF into a Word document you can edit. It works best on PDFs that contain real text rather than scans. | Input PDF, output `.docx` |
| 22 | DOCX → PDF | Turns a Word document into a PDF. Needs Microsoft Word or LibreOffice. | Input `.docx`, output PDF |
| 5 | Images → PDF | Puts pictures into one PDF, one picture per page. Works with JPG, PNG, TIFF, BMP, GIF and WebP. A file has to really be the type its name says; a renamed file of another type is refused. JPG, PNG and TIFF pictures are copied in without any loss of quality, and photos are turned the right way up. | Image folder, output name, optional list of file names |
| 16 | PDF → images | Saves each page as a picture (`page_0001.png`, `page_0002.png` and so on). | Input PDF, output folder, DPI, format (`png` or `jpg`) |
| 7 | Extract text | Saves the text of a PDF in a `.txt` file. Press Enter at the output question to save it next to the PDF under the same name. | Input PDF, output `.txt` |
| 15 | Extract images | Saves the pictures that are inside a PDF into a folder. | Input PDF, output folder |

Notes on option 5:
- If you leave the list of file names empty, JAP-T uses every picture in the folder in name order, with `img2` before `img10`.
- To choose the order yourself, type the names with commas between them, for example `cover.jpg, page1.png, page2.jpg`.
- If you give only a name for the output, such as the default `merged_output.pdf`, the PDF is saved in the image folder.
- If a listed file is missing or can't be read, JAP-T names it and doesn't create the PDF.
- A TIFF file with several pages becomes several PDF pages. Transparent parts of PNG, GIF or WebP pictures become white.

Notes on option 22: JAP-T uses Microsoft Word if it is installed, and LibreOffice otherwise. With LibreOffice, JAP-T uses its own separate LibreOffice settings. This means it won't interfere with a LibreOffice window you already have open, and it never checks for or installs LibreOffice updates. The first conversion takes a little longer while those settings are created.

Notes on DPI (options 16 and 21): DPI sets how sharp the pictures are. 150 is enough for viewing on screen. 300 is better for printing but gives larger files.

### Organising pages

| # | Option | What it does | Questions |
|---|---|---|---|
| 3 | Merge PDFs | Joins several PDFs into one, in the order you list them. Bookmarks and form fields are kept. | Input PDFs separated by commas, then the output PDF |
| 4 | Split PDF | Splits a PDF into smaller files. The modes are described below. | Input PDF, mode, output folder, file name prefix, and page range or chunk size |
| 10 | Rotate pages | Turns pages clockwise by 90, 180 or 270 degrees. Leave the page list empty to turn every page. | Input, output, angle, pages (optional) |
| 11 | Delete pages | Removes the pages you choose. It won't delete every page. | Input, output, pages to delete |
| 12 | Reorder pages | Puts the pages in a new order. Type the current page numbers in the order you want: `3,1,2` puts page 3 first. | Input, output, new order |
| 24 | Insert pages | Adds blank pages, or pages copied from another PDF, at the position you choose. Bookmarks still point to the right pages afterwards. | Input, output, position, then either the other PDF and its pages or the number of blank pages |
| 25 | Bookmarks | Shows or adds bookmarks, the list of links in a PDF reader's side panel. | See below |

Split modes:

- `single` saves every page as its own file (`page_0001.pdf`, `page_0002.pdf` and so on).
- `range` copies the pages you choose into one file called `split_pages.pdf`. If the range goes past the last page, it stops at the last page.
- `chunk` cuts the PDF into equal parts. A chunk size of 10 gives pages 1–10, 11–20 and so on (`chunk_0001.pdf`, …).

JAP-T asks for both a page range and a chunk size every time, but only uses the one that belongs to the mode you chose. Press Enter for the other one.

Insert pages: the position is the page that the new pages go after. `0` puts them before page 1, and `3` puts them after page 3. Blank pages are the same size as the page before them. When copying pages from another PDF, leave the page list empty to copy all of them.

Bookmarks (option 25) first asks what you want to do:

- `show` lists the bookmarks. Bookmarks that belong under another one are indented.
- `add` adds one bookmark with a title and the page it opens. It is placed in page order among the others.

### Making files smaller and searchable

| # | Option | What it does |
|---|---|---|
| 6 | Compress PDF | Makes the file smaller, mostly by shrinking the pictures in it. If it can't make the file any smaller, you get an unchanged copy, never a bigger file. Works much better when Ghostscript is installed. |
| 2 | OCR PDF | Reads the words in a scanned PDF so you can search, select and copy them. Needs Tesseract and Ghostscript. |
| 21 | Convert selected pages to non-OCR | Does the opposite of OCR for the pages you choose, turning them back into plain pictures without selectable text. The other pages stay as they are. |
| 27 | Save as PDF/A | Converts a PDF to PDF/A, a format for keeping documents readable for many years. Archives, courts and government offices often ask for it. Needs Tesseract and Ghostscript. Answer `y` to the extra question to make scanned pages searchable at the same time. The result can be larger than the original, because PDF/A includes all fonts in the file. |

The OCR questions are explained below. You can press Enter to accept the default for any of them.

- Language: the language of the document. `eng` is English. For a document in more than one language, join them with `+`, for example `eng+jpn`. Each language has to be installed in Tesseract (see [Optional](#optional)).
- Deskew: straightens pages that were scanned slightly crooked.
- Rotate pages: turns pages that were scanned sideways or upside down.
- Remove background: cleans up grey or speckled backgrounds.
- Optimize (0–3): how hard JAP-T tries to make the result smaller. 1 is a safe choice.
- Force OCR: reads the pages again even if the PDF already contains text. Use this if you get the message "Prior OCR/text detected".
- Skip existing text: only reads the pages that don't contain text yet.

### Passwords

| # | Option | What it does |
|---|---|---|
| 8 | Encrypt PDF | Adds a password. The PDF can't be opened without it. Uses AES-256 encryption. |
| 9 | Decrypt PDF | Removes the password from a PDF, if you know the password. |

Nothing appears on screen while you type the password. This is deliberate, so that nobody can read it over your shoulder. Type it and press Enter. When you add a password with option 8, you type it twice to rule out typing mistakes.

A forgotten password can't be recovered, so keep an unprotected copy of the PDF somewhere safe.

### Adding text to pages

| # | Option | What it does |
|---|---|---|
| 13 | Add header/footer | Adds text at the top, the bottom or both, on every page. |
| 14 | Watermark | Adds large, faint text across the middle of every page, such as `DRAFT` or `CONFIDENTIAL`. |

Header and footer: `{page}` is replaced by the page number and `{pages}` by the total number of pages. For example, the footer `Page {page} of {pages}` prints "Page 3 of 10" on page 3. The margin is the distance from the edge of the page, measured in points (72 points = 1 inch).

Watermark: "Rotate" is the angle in degrees. 45 is diagonal, and decimals such as 22.5 are allowed. "Opacity" goes from 0 (invisible) to 1 (fully solid grey), and 0.15 gives a light watermark.

Both options also work with text in other scripts, such as Japanese, Chinese, Korean, Russian or Hindi. JAP-T chooses a suitable font.

### Removing private information

| # | Option | What it does |
|---|---|---|
| 26 | Redact text | Removes words or phrases, such as names, account numbers or addresses, and puts black boxes in their place. |

Type the text you want removed. To remove several things at once, separate them with `|`, for example `John Smith | 12345678`. It doesn't matter whether you use capital letters.

Drawing a black box over text only hides it, and the text can often still be copied out. Redaction deletes the text itself, so it can't be copied, searched or recovered from the new file.

Text can also hide outside the page, and JAP-T deals with that too:

- Comments (sticky notes) that contain the text are deleted.
- In form fields, the text is replaced with `[redacted]`.
- Attached files that contain the text are deleted. JAP-T can't look inside compressed files such as Word documents or ZIPs, so it lists any attached files it leaves in place. Check those yourself.

There are some limits to be aware of:

- Scanned pages are pictures, so the words on them can't be found. Run OCR (option 2) first, then redact the result. JAP-T lists the pages that contain no text.
- The title, author and bookmarks are stored outside the pages, so redaction doesn't change them. JAP-T warns you if your text appears there. You can change them with options 18 and 25.
- If none of the text is found, JAP-T doesn't create a file.

Open the redacted PDF and check it before you send it to anyone.

### Information and metadata

| # | Option | What it does |
|---|---|---|
| 19 | PDF info | Shows how many pages a PDF has and whether it has a password. |
| 17 | Show metadata | Shows the details stored inside the PDF, such as title, author, the program that created it and dates. |
| 18 | Set metadata | Changes those details. Anything you don't mention stays as it is. Some PDFs store these details twice, and JAP-T changes both copies. |
| 23 | Check setup | Shows which optional programs JAP-T has found and which features need something installed. |

Set metadata expects the details in a fixed format called JSON, like this:

```
{"/Title": "Annual Report 2026", "/Author": "Jane Doe"}
```

The usual keys are `/Title`, `/Author`, `/Subject` and `/Keywords`. Type the slashes, quote marks and curly brackets exactly as shown. To remove a detail, give it an empty value, for example `{"/Author": ""}`.

### Batch processing

| # | Option | What it does |
|---|---|---|
| 20 | Batch folder | Runs the same job on every PDF in a folder. |

These are the jobs you can choose. Each one creates a new file for every PDF:

| Job | Creates |
|---|---|
| `ocr` | `name_ocr.pdf` |
| `compress` | `name_compressed.pdf` |
| `extract-text` | `name.txt` |
| `watermark` | `name_watermarked.pdf` |
| `rotate` | `name_rotated.pdf` |
| `header-footer` | `name_header_footer.pdf` |

After you choose a job, JAP-T asks the same questions as the single-file option, for example the watermark text or the rotation angle, and uses your answers for every file.

- "Glob" selects which files to include. Press Enter to accept `*.pdf`, which means all PDFs. `invoice*.pdf` would select only the PDFs whose names start with "invoice".
- Leave the output folder empty to save the results next to the original files.
- If you run the same job again in the same folder, the files created last time are skipped, so you won't get names like `name_rotated_rotated.pdf`. The earlier results are replaced with new ones.
- If some files fail, JAP-T lists them and prints `Failed.` The other files are still processed.

---

## 7. Page numbers and ranges

Pages are numbered from 1. Wherever JAP-T asks for pages, you can combine single pages and ranges, separated by commas:

| You type | Pages selected |
|---|---|
| `5` | page 5 |
| `1-3` | pages 1, 2 and 3 |
| `1-3,6` | pages 1, 2, 3 and 6 |
| `2,9-12,16` | pages 2, 9, 10, 11, 12 and 16 |

Spaces are allowed (`1 - 3, 6`), and a page typed twice is only used once. Option 19 shows how many pages a PDF has.

---

## 8. Updating or removing JAP-T

### Updating JAP-T

1. Download and extract the new version into a new folder, the same way as in [First-time setup](#3-first-time-setup).
2. Double-click `setupEnv.bat` in the new folder.
3. Once the new version works, you can delete the old folder.

Your PDFs are not stored in the JAP-T folder, so updating doesn't affect them.

If you got JAP-T with Git rather than as a ZIP file, run `git pull` in the JAP-T folder and then double-click `setupEnv.bat`.

### Moving to a newer Python

If you install a newer version of Python later, for example 3.14 after using 3.13, JAP-T carries on using the old version until you rebuild its setup:

1. Close JAP-T.
2. In the JAP-T folder, delete the folder called `venv`.
3. Double-click `setupEnv.bat`. It uses the newest supported Python it can find.

You can uninstall the old Python afterwards if nothing else on your computer needs it.

### Removing JAP-T

1. Delete the JAP-T folder.
2. If you have converted Word documents with LibreOffice, JAP-T also created a settings folder. To remove it, click the address bar in File Explorer, type `%LOCALAPPDATA%`, press Enter, and delete the folder called `JAP-T`.

Python, Tesseract, Ghostscript and LibreOffice are separate programs. If you don't need them any more, uninstall them from Settings → Apps like any other program.

---

## 9. Using the command line (optional)

The menu is enough for most people, and you can skip this section. The command line is quicker for jobs you repeat often, and it lets you use JAP-T in scripts.

To open a Command Prompt in the JAP-T folder, open the folder in File Explorer, click the address bar, type `cmd` and press Enter. Commands look like this:

```bat
venv\Scripts\python.exe src\pdfsuite.py merge --out combined.pdf a.pdf b.pdf c.pdf
venv\Scripts\python.exe src\pdfsuite.py compress --in big.pdf --out small.pdf
venv\Scripts\python.exe src\pdfsuite.py watermark --in report.pdf --out draft.pdf --text DRAFT
venv\Scripts\python.exe src\pdfsuite.py split --in book.pdf --mode chunk --chunk-size 20 --out-dir chapters
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Scans --op ocr --lang eng
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op watermark --text DRAFT --out-dir C:\Drafts
venv\Scripts\python.exe src\pdfsuite.py batch --folder C:\Reports --op header-footer --footer "Page {page} of {pages}"
```

- Put quote marks around paths that contain spaces, for example `--in "C:\My Files\report.pdf"`.
- Unlike the menu, the command line accepts the same file for `--in` and `--out`, and overwrites it without asking.
- For `encrypt` and `decrypt`, leave out `--password` and JAP-T will ask for the password without showing it. A password typed after `--password` may be saved in your command history.

To list all commands:

```bat
venv\Scripts\python.exe src\pdfsuite.py --help
```

To see the options for one command, put `--help` after the command name, for example `venv\Scripts\python.exe src\pdfsuite.py ocr --help`.

| Command | Menu option |
|---|---|
| `docx` | 1. PDF → DOCX |
| `ocr` | 2. OCR PDF |
| `merge` | 3. Merge PDFs |
| `split` | 4. Split PDF |
| `images-to-pdf` (or the older name `jpg-merge`) | 5. Images → PDF |
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
| `redact` | 26. Redact text (use `--text` once for each phrase) |
| `pdfa` | 27. Save as PDF/A (add `--ocr` to make scans searchable) |
| `menu` | Opens the menu |

Put `--log-level WARNING` before the command name to see only warnings and errors, or `--log-level DEBUG` to see more detail when something goes wrong.

---

## 10. Troubleshooting

| Message or problem | What to do |
|---|---|
| "Windows protected your PC" | Click "More info", then "Run anyway". Windows shows this for files downloaded from the internet. |
| `Python is not installed.` during setup | Install Python 3.14 (see [What you need](#2-what-you-need)) and run `setupEnv.bat` again. |
| `Found Python 3.x, but JAP-T needs Python 3.11, 3.12, 3.13 or 3.14.` | Your Python version is too new or too old for JAP-T. Install Python 3.14 as well (see [What you need](#2-what-you-need)). You can keep the other version. Then run `setupEnv.bat` again. |
| `Setup did not finish.` | The message just above it says what went wrong, often a missing internet connection. Fix that and run `setupEnv.bat` again. |
| `JAP-T is not set up yet.` when starting | Run `setupEnv.bat` first. |
| `Missing Python package: …` | Setup didn't finish. Run `setupEnv.bat` again. |
| `Input PDF not found` | The location is wrong. Use "Copy as path" in File Explorer (see [Typing file locations](#typing-file-locations)). |
| OCR fails, or the message mentions Tesseract or Ghostscript | Install both (see [What you need](#2-what-you-need)), then close and reopen JAP-T. Option 23 shows whether they were found. |
| `Prior OCR/text detected` | The PDF already contains text. Answer `y` to "Force OCR" or to "Skip existing text". |
| PDF/A fails with `needs Tesseract and Ghostscript` | Install both (see [What you need](#2-what-you-need)). PDF/A needs them even when no OCR is done. |
| `None of the text was found` (redact) | Check the spelling. If the page is a scan, run OCR (option 2) first and then redact the result. |
| `No conversion backend available` (DOCX → PDF) | Install Microsoft Word or LibreOffice. Option 23 shows whether either was found. |
| `File has not been decrypted`, or other password errors | The PDF has a password. Remove it with option 9, then run the job on the unprotected copy. |
| `Incorrect password` | Passwords are case-sensitive, so check Caps Lock. Remember that nothing appears on screen while you type. |
| `page … out of bounds` | You asked for a page after the last one. Option 19 shows how many pages the PDF has. |
| Compress saved 0% | The PDF couldn't be made any smaller. Installing Ghostscript helps with scanned PDFs and PDFs with many photos. |
| `Failed.` after a batch | Some files failed. Their names are listed above `Failed.` The other files were processed. |

If none of this helps, run the job from the command line with `--log-level DEBUG` (see [section 9](#9-using-the-command-line-optional)) and include the output when you ask for help.

---

## 11. Words used in this guide

| Word | Meaning |
|---|---|
| OCR | Short for "optical character recognition". The computer reads the words in a picture of a page so you can search and copy them. |
| Scan, scanned PDF | A PDF whose pages are pictures, for example from a scanner or a phone camera. You can't select the text in it until it has been through OCR. |
| Redact | To remove information so that it can't be recovered. |
| PDF/A | A type of PDF made for keeping documents readable for many years. Archives, courts and government offices often ask for it. |
| Metadata | Details stored inside a file, such as its title and author. |
| DPI | Short for "dots per inch". It sets how sharp a picture is. A higher number gives sharper pictures and larger files. |
| Watermark | Faint text printed across a page, such as "DRAFT". |
| Encrypt, decrypt | To add or remove a password. |
| Glob | A pattern for choosing files by name. `*` stands for any text, so `*.pdf` means every PDF. |
| Command Prompt | A window where you type commands instead of clicking. It is only needed for the optional [command line](#9-using-the-command-line-optional). |
