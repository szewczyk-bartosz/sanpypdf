# sanpypdf

Rasterises PDFs into images and then back into a PDF, stripping everything that isn't visible on the page. Potential use is for PDFs you don't trust, as an extra layer of security.

## Usage

```sh
pipx install sanpypdf      # or: uv tool install sanpypdf
sanpypdf INPUT_DIR [-o OUTPUT_DIR]
```

Every `.pdf` file under `INPUT_DIR` is processed, and ends up in `INPUT_DIR/sanpy-output` unless -o is given (output always preserves input directory structure).
Re-running overwrites the previous output.

## Design

**Rasterise** - Blunt tool, but it is simple, no hidden malicious bits can survive if the whole file is just a bunch of images. If you want text to be selectable, I recommend doing an OCR pass with a dedicated tool.

**Chunked, incremental saves** - Pages are rendered 32 at a time and appended to the output with incremental save. Memory usage stays flat, however long the document.

**No built-in sandbox** - The only thing I can think of that may go wrong is a vulnerability in MuPDF itself. If that is part of your threat model, isolate the whole process with bubblewrap or something similar.
