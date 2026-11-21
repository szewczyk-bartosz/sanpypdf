# sanpypdf

Strips everything out of a PDF that isn't visible on the page (JavaScript,
embedded files, forms, links, metadata, hidden text) by rendering each page to
an image and building a new PDF from those images.

## Usage

```sh
pip install sanpypdf
sanpypdf INPUT_DIR [-o OUTPUT_DIR]
```

Every `*.pdf` under `INPUT_DIR` is processed recursively. The output keeps the
same directory layout and goes to `INPUT_DIR/sanpy-output` unless `-o` is given.
Re-running overwrites previous output.

## Design

**Rasterise, don't filter.** Trying to remove the dangerous parts of a PDF
means knowing every way a PDF can be dangerous. Turning each page into a
picture avoids that problem: nothing survives except pixels. The downside is
that text is no longer selectable or searchable, and files may get bigger.

! You can do an OCR pass afterwards if you want !

**Chunked, incremental saves.** Pages are rendered 32 at a time and appended
to the output with an incremental save. Memory use stays flat however long
the document is.

**No built-in sandbox.** Parsing an untrusted PDF can only go wrong through a
bug in MuPDF itself. If that's part of your threat model, isolate the whole
process with bubblewrap or something similar
