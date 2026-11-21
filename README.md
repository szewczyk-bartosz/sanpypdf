# sanpypdf

Strips everything out of a PDF that isn't visible on the page (JavaScript,
embedded files, forms, links, metadata, hidden text) by rendering each page to
an image and building a new PDF from those images.

## Usage

```sh
nix develop               # or: pip install pymupdf
python main.py INPUT_DIR [-o OUTPUT_DIR]
```

Every `*.pdf` under `INPUT_DIR` is processed recursively. The output keeps the
same directory layout and goes to `INPUT_DIR/sanpy-output` unless `-o` is given.
Re-running overwrites previous output.

## Design

**Rasterise, don't filter.** Trying to remove the dangerous parts of a PDF
means knowing every way a PDF can be dangerous. Turning each page into a
picture avoids that problem: nothing survives except pixels. The downside is
that text is no longer selectable or searchable, and files may get bigger.

You can do an OCR pass afterwards if you want

**PyMuPDF only.** It handles opening, rendering and writing, so there's no
need for poppler, Pillow or temp files. It's one dependency to install and
nothing to clean up afterwards.

**Chunked, incremental saves.** Pages are rendered 32 at a time and appended
to the output with an incremental save. Memory use stays flat however long
the document is.

**No built-in sandbox.** Parsing an untrusted PDF can only go wrong through a
bug in MuPDF itself. If that's part of your threat model, isolate the whole
process. That's the caller's job, and you'd want it regardless of what this
tool does. For example, with bubblewrap (which is included in the dev shell):

```sh
mkdir -p out
bwrap --ro-bind /nix/store /nix/store \
      --ro-bind main.py /main.py \
      --ro-bind in /in --bind out /out \
      --proc /proc --dev /dev \
      --unshare-all --die-with-parent --clearenv \
      "$(command -v python)" /main.py /in -o /out
```

The process gets no network access, read-only access to the input, and can
only write to `out`.
