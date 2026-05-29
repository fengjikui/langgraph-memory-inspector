from __future__ import annotations

import argparse
import struct
from pathlib import Path


DEFAULT_ASSET = Path("docs/assets/github-social-preview.png")
EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 640
MAX_BYTES = 1_000_000


def validate_social_preview(path: Path = DEFAULT_ASSET) -> dict[str, int | str]:
    """Validate the GitHub social preview asset without image dependencies."""
    if not path.exists():
        raise ValueError(f"Social preview asset does not exist: {path}")
    size_bytes = path.stat().st_size
    if size_bytes >= MAX_BYTES:
        raise ValueError(f"Social preview asset must be under 1 MB, got {size_bytes} bytes")

    width, height, color_type = _read_png_header(path)
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise ValueError(
            "Social preview asset must be "
            f"{EXPECTED_WIDTH} x {EXPECTED_HEIGHT}, got {width} x {height}"
        )
    if color_type == 4 or color_type == 6:
        raise ValueError("Social preview asset should use a solid non-transparent background")

    return {
        "path": str(path),
        "format": "PNG",
        "width": width,
        "height": height,
        "size_bytes": size_bytes,
        "max_bytes": MAX_BYTES,
    }


def _read_png_header(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()[:33]
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Social preview asset must be a PNG file: {path}")
    chunk_length = struct.unpack(">I", data[8:12])[0]
    chunk_type = data[12:16]
    if chunk_type != b"IHDR" or chunk_length < 13:
        raise ValueError(f"Social preview asset has an invalid PNG IHDR chunk: {path}")
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    return width, height, color_type


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the GitHub social preview asset.")
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_ASSET),
        help=f"Path to the social preview asset. Defaults to {DEFAULT_ASSET}.",
    )
    args = parser.parse_args()
    result = validate_social_preview(Path(args.path))
    print(
        "OK: {path} is {width}x{height} PNG, {size_bytes} bytes "
        "(limit: < {max_bytes} bytes).".format(**result)
    )


if __name__ == "__main__":
    main()
