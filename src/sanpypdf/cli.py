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
    try:
        with pymupdf.open(path) as doc:
            return doc.page_count
    except (pymupdf.FileDataError, RuntimeError) as e:
        sys.exit(f"couldn't open {path}: {e}")


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


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()
    log.info("input:  %s", cfg.input_dir)
    log.info("output: %s", cfg.output_dir)

    files = find_pdfs(cfg)
    for f in files:
        f.page_count = get_page_count(cfg.input_dir / f.path)
        log.info("found %s (%d pages)", f.path, f.page_count)
    total = sum(f.size for f in files) / 1024**2
    log.info("total size: %.2f MB", total)

    for f in files:
        process_file(cfg, f)


if __name__ == "__main__":
    main()
