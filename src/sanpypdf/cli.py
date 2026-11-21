"""Flatten PDFs into images to strip anything that isn't visible on the page.

Each page is rendered to a JPEG and the PDF is rebuilt from the images.
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf

CHUNK_SIZE = 32
PPI = 300
JPEG_QUALITY = 75 

log = logging.getLogger(__name__)


@dataclass
class Config:
    input_dir: Path
    output_dir: Path


@dataclass
class InputFile:
    path: Path  # relative to input_dir
    size: int
    page_count: int = 0


def load_config():
    parser = argparse.ArgumentParser(description="Sanitize PDFs by rasterizing every page.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, help="default: INPUT_DIR/sanpy-output")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = (args.output_dir or input_dir / "sanpy-output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return Config(input_dir, output_dir)


def find_pdfs(cfg):
    files = []
    for path in sorted(cfg.input_dir.rglob("*.pdf")):
        if path.is_relative_to(cfg.output_dir):
            continue
        files.append(InputFile(path.relative_to(cfg.input_dir), path.stat().st_size))
    return files


def get_page_count(path):
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("encrypted, needs a password")
        return doc.page_count


def chunks(count, size):
    for first in range(1, count + 1, size):
        yield first, min(first + size - 1, count)


def add_pages(dst, src, first, last):
    for page in src.pages(first - 1, last):
        jpeg = page.get_pixmap(dpi=PPI).tobytes("jpeg", jpg_quality=JPEG_QUALITY)
        new_page = dst.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=jpeg)


def process_file(cfg, file):
    dst_path = cfg.output_dir / file.path
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    log.info("%s (%d pages)", file.path, file.page_count)

    # Write the output in chunks so whole document doesnt go in memory
    try:
        with pymupdf.open(cfg.input_dir / file.path) as src:
            for first, last in chunks(file.page_count, CHUNK_SIZE):
                log.info("  pages %d-%d", first, last)
                if first == 1:
                    with pymupdf.open() as dst:
                        add_pages(dst, src, first, last)
                        dst.save(dst_path)
                else:
                    with pymupdf.open(dst_path) as dst:
                        add_pages(dst, src, first, last)
                        dst.saveIncr()
    except BaseException:
        # don't leave a half-written file that looks like a finished one
        dst_path.unlink(missing_ok=True)
        raise


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()
    log.info("input:  %s", cfg.input_dir)
    log.info("output: %s", cfg.output_dir)

    # Inputs are untrusted, so any one of them can fail in any way. Log it and
    # move on rather than letting one bad file stop the batch.
    failed = []
    files = []
    for f in find_pdfs(cfg):
        try:
            f.page_count = get_page_count(cfg.input_dir / f.path)
        except Exception as e:
            log.error("skipping %s: %s", f.path, e)
            failed.append(f.path)
            continue
        log.info("found %s (%d pages)", f.path, f.page_count)
        files.append(f)
    total = sum(f.size for f in files) / 1024**2
    log.info("total size: %.2f MB", total)

    for f in files:
        try:
            process_file(cfg, f)
        except Exception as e:
            log.error("failed %s: %s", f.path, e)
            failed.append(f.path)

    if failed:
        log.error("%d file(s) failed:", len(failed))
        for path in failed:
            log.error("  %s", path)
        sys.exit(1)


if __name__ == "__main__":
    main()
