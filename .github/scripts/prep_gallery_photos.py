"""Prepares photos for the site's photo gallery.

Takes a folder of originals (HEIC/JPG/PNG/WebP, any mix), converts each to a
web-sized JPEG with all EXIF metadata stripped (GPS included), and writes the
results into images/gallery/<section>/.

Run from the repo root:
    python3 .github/scripts/prep_gallery_photos.py ~/Desktop/hiking_picks hiking
    python3 .github/scripts/prep_gallery_photos.py ~/Desktop/city_picks cityscapes

Any <section> name works; the gallery include renders images/gallery/<section>/
via {% include photo-gallery.html folder="<section>" %}.

Gallery order = filename order, so rename files with number prefixes
(01_torrey_pines.heic, 02_cuyamaca.heic, ...) before or after running.
Re-running overwrites existing outputs with the same name (idempotent).

Requires macOS (uses sips for HEIC decode) and Pillow (present in the
anaconda python3 on this machine).
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

MAX_EDGE = 1600
JPEG_QUALITY = 85
HEIC_EXTS = {".heic", ".heif"}
OTHER_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def sanitize_stem(stem: str) -> str:
    """Lowercase the filename stem and reduce it to url-friendly characters."""
    stem = stem.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_-]", "", stem) or "photo"


def load_image(path: Path, tmp_dir: Path) -> Image.Image:
    """Open an original, routing HEIC through sips since Pillow can't read it."""
    if path.suffix.lower() in HEIC_EXTS:
        tmp_jpg = tmp_dir / (path.stem + ".jpg")
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp_jpg)],
            check=True,
            capture_output=True,
        )
        return Image.open(tmp_jpg)
    return Image.open(path)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 .github/scripts/prep_gallery_photos.py <source_folder> <section>")

    source = Path(sys.argv[1]).expanduser()
    section = sys.argv[2].strip("/")
    if not source.is_dir():
        sys.exit(f"Source folder not found: {source}")

    dest = Path("images/gallery") / section
    if not Path("images/gallery").is_dir():
        sys.exit("Run from the repo root (images/gallery/ not found here).")
    dest.mkdir(parents=True, exist_ok=True)

    originals = sorted(
        p for p in source.iterdir()
        if p.is_file() and p.suffix.lower() in HEIC_EXTS | OTHER_EXTS
    )
    if not originals:
        sys.exit(f"No images (heic/jpg/png/webp) found in {source}")

    written = 0
    gps_stripped = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for path in originals:
            image = load_image(path, tmp_dir)

            # Count GPS occurrences before the strip, for the summary line
            if 34853 in image.getexif():
                gps_stripped += 1

            # Bake orientation into pixels, flatten alpha, cap the long edge
            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

            out = dest / (sanitize_stem(path.stem) + ".jpg")
            image.save(out, "JPEG", quality=JPEG_QUALITY)
            written += 1
            size_kb = out.stat().st_size // 1024
            print(f"{path.name} -> {out} ({image.size[0]}x{image.size[1]}, {size_kb}KB)")

    print(f"\nDone: {written} photos into {dest}/ ({gps_stripped} had GPS data; all EXIF stripped).")
    print("Display order follows filename order; prefix files 01_, 02_, ... to control it.")


if __name__ == "__main__":
    main()
