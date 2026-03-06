from __future__ import annotations

import csv
import fnmatch
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from PIL import Image, UnidentifiedImageError

from logo_to_square.img_processing_methods.common_ops import resize_method
from logo_to_square.img_processing_methods.getdominantcolor import ColorThief
from logo_to_square.img_processing_methods.opaque_ops import get_bg_color
from logo_to_square.img_processing_methods.transparent_ops import has_transparency

RGBColor = Tuple[int, int, int]
SUPPORTED_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".ico",
    ".ppm",
}
PRESETS: Dict[str, Dict[str, Union[str, int, float]]] = {
    "app-icon": {
        "target_size": 512,
        "output_format": "png",
        "quality": 100,
        "fit": "contain",
        "padding": 0.10,
    },
    "marketplace": {
        "target_size": 1024,
        "output_format": "webp",
        "quality": 92,
        "fit": "contain",
        "padding": 0.06,
    },
    "social": {
        "target_size": 1200,
        "output_format": "jpeg",
        "quality": 90,
        "fit": "cover",
        "padding": 0.00,
    },
}


def _relative_luminance(color: RGBColor) -> float:
    red, green, blue = color
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _parse_background(background: str) -> Optional[RGBColor]:
    value = background.strip().lower()
    if value == "auto":
        return None
    if value == "white":
        return (255, 255, 255)
    if value == "black":
        return (0, 0, 0)
    if value.startswith("#") and len(value) == 7:
        try:
            return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
        except ValueError as exc:
            raise ValueError(f"Invalid background hex color: {background}") from exc
    raise ValueError("background must be one of: auto, black, white, or #RRGGBB")


def _normalize_format(output_format: str) -> str:
    value = output_format.strip().lower()
    return "jpeg" if value == "jpg" else value


def _pil_format(output_format: str) -> str:
    mapping = {"jpeg": "JPEG", "tif": "TIFF"}
    return mapping.get(output_format.lower(), output_format.upper())


def _choose_transparent_fill(img_path: Path, quality: int) -> RGBColor:
    dominant_color = ColorThief(str(img_path)).get_color(quality=quality)
    return (0, 0, 0) if _relative_luminance(dominant_color) > 150 else (255, 255, 255)


def _prepare_output_path(
    out_path: Union[str, Path], filename: str, output_format: str
) -> Path:
    output_dir = Path(out_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{filename}_square.{_normalize_format(output_format)}"


def _resolve_preset(
    *,
    preset: Optional[str],
    target_size: Optional[int],
    output_format: str,
    quality: int,
    fit: str,
    padding: float,
) -> Tuple[int, str, int, str, float]:
    if preset is None:
        resolved_size = int(target_size) if target_size is not None else 200
        return resolved_size, _normalize_format(output_format), int(quality), fit, float(padding)

    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Choose from: {', '.join(sorted(PRESETS))}")

    values = PRESETS[preset]
    resolved_size = int(values["target_size"]) if target_size is None else int(target_size)
    resolved_output = (
        _normalize_format(str(values["output_format"]))
        if output_format == "webp"
        else _normalize_format(output_format)
    )
    resolved_quality = int(values["quality"]) if quality == 95 else int(quality)
    resolved_fit = str(values["fit"]) if fit == "contain" else fit
    resolved_padding = float(values["padding"]) if padding == 0.0 else float(padding)
    return resolved_size, resolved_output, resolved_quality, resolved_fit, resolved_padding


def _fit_contain_square(
    img: Image.Image,
    target_size: int,
    fit_size: int,
    background_color: RGBColor,
    use_alpha: bool,
) -> Image.Image:
    resized = resize_method(img, fit_size)
    canvas_mode = "RGBA" if use_alpha else "RGB"
    fill = (*background_color, 255) if use_alpha else background_color
    result = Image.new(canvas_mode, (target_size, target_size), fill)
    paste_x = (target_size - resized.size[0]) // 2
    paste_y = (target_size - resized.size[1]) // 2
    if use_alpha:
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")
        result.paste(resized, (paste_x, paste_y), resized)
    else:
        if resized.mode != "RGB":
            resized = resized.convert("RGB")
        result.paste(resized, (paste_x, paste_y))
    return result


def _fit_cover_square(img: Image.Image, target_size: int, use_alpha: bool) -> Image.Image:
    width, height = img.size
    if width <= 0 or height <= 0:
        raise ValueError("Input image has invalid dimensions")
    scale = target_size / min(width, height)
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    cropped = resized.crop((left, top, left + target_size, top + target_size))
    return cropped.convert("RGBA" if use_alpha else "RGB")


def squareify(
    img_path: Union[str, Path],
    target_size: Optional[int],
    out_path: Union[str, Path],
    filename: str,
    *,
    output_format: str = "webp",
    quality: int = 95,
    background: str = "auto",
    fit: str = "contain",
    padding: float = 0.0,
    preset: Optional[str] = None,
) -> Path:
    parsed_size, parsed_format, parsed_quality, parsed_fit, parsed_padding = _resolve_preset(
        preset=preset,
        target_size=target_size,
        output_format=output_format,
        quality=quality,
        fit=fit,
        padding=padding,
    )
    if parsed_size <= 0:
        raise ValueError("target_size must be a positive integer")
    if not 1 <= parsed_quality <= 100:
        raise ValueError("quality must be between 1 and 100")
    if parsed_fit not in {"contain", "cover"}:
        raise ValueError("fit must be either 'contain' or 'cover'")
    if not 0.0 <= parsed_padding <= 0.45:
        raise ValueError("padding must be between 0.0 and 0.45")

    input_path = Path(img_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    parsed_bg = _parse_background(background)
    output_file = _prepare_output_path(out_path, filename, parsed_format)

    try:
        with Image.open(input_path) as src:
            img = src.copy()
            transparent_source = has_transparency(img)

            if transparent_source:
                fill_color = (
                    parsed_bg
                    if parsed_bg is not None
                    else _choose_transparent_fill(input_path, quality=10)
                )
                use_alpha = True
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                fill_color = parsed_bg if parsed_bg is not None else get_bg_color(img)
                use_alpha = False

            fit_size = max(1, int(parsed_size * (1 - (2 * parsed_padding))))
            if parsed_fit == "cover":
                squared = _fit_cover_square(img, parsed_size, use_alpha)
            else:
                squared = _fit_contain_square(
                    img=img,
                    target_size=parsed_size,
                    fit_size=fit_size,
                    background_color=fill_color,
                    use_alpha=use_alpha,
                )

            if parsed_format == "jpeg" and squared.mode != "RGB":
                squared = squared.convert("RGB")

            save_kwargs = {"quality": parsed_quality}
            if parsed_format in {"png", "bmp", "tiff", "gif", "ico", "ppm"}:
                save_kwargs.pop("quality", None)
            squared.save(output_file, format=_pil_format(parsed_format), **save_kwargs)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupt image: {input_path}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot save output in format '{parsed_format}': {exc}") from exc

    return output_file


def _iter_input_files(
    input_dir: Path,
    *,
    recursive: bool,
    include_patterns: List[str],
    exclude_patterns: List[str],
) -> Iterable[Path]:
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    for path in sorted(iterator):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        relative = path.relative_to(input_dir).as_posix()
        if include_patterns and not any(
            fnmatch.fnmatch(relative, pattern) for pattern in include_patterns
        ):
            continue
        if exclude_patterns and any(
            fnmatch.fnmatch(relative, pattern) for pattern in exclude_patterns
        ):
            continue
        yield path


def _write_report(report_path: Path, rows: List[Dict[str, str]]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.suffix.lower() == ".json":
        with report_path.open("w", encoding="utf-8") as fp:
            json.dump(rows, fp, indent=2)
        return
    if report_path.suffix.lower() == ".csv":
        with report_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=["input", "output", "status", "message"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return
    raise ValueError("report_path must end with .json or .csv")


def _derive_output_path(
    out_img_path: str,
    file_path: Path,
    input_dir: Path,
    output_format: str,
) -> Path:
    rel_parent = file_path.relative_to(input_dir).parent
    out_dir = Path(out_img_path) / rel_parent
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{file_path.stem}_square.{_normalize_format(output_format)}"


def _default_name_for_single_input(in_img_path: str) -> str:
    return Path(in_img_path).stem


def process_images(
    *,
    in_img_path: Optional[str],
    in_dir: Optional[str],
    target_size: Optional[int],
    out_img_path: str,
    filename: Optional[str],
    output_format: str,
    quality: int,
    background: str,
    overwrite: bool,
    fit: str = "contain",
    padding: float = 0.0,
    preset: Optional[str] = None,
    recursive: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    dry_run: bool = False,
    report_path: Optional[str] = None,
) -> None:
    include_patterns = include or ["*"]
    exclude_patterns = exclude or []
    rows: List[Dict[str, str]] = []

    if in_dir:
        input_dir = Path(in_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        for file_path in _iter_input_files(
            input_dir,
            recursive=recursive,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        ):
            out_file = _derive_output_path(out_img_path, file_path, input_dir, output_format)
            if out_file.exists() and not overwrite:
                rows.append(
                    {
                        "input": str(file_path),
                        "output": str(out_file),
                        "status": "skipped",
                        "message": "exists",
                    }
                )
                continue
            if dry_run:
                rows.append(
                    {
                        "input": str(file_path),
                        "output": str(out_file),
                        "status": "planned",
                        "message": "dry-run",
                    }
                )
                continue
            try:
                squareify(
                    file_path,
                    target_size,
                    out_file.parent,
                    file_path.stem,
                    output_format=output_format,
                    quality=quality,
                    background=background,
                    fit=fit,
                    padding=padding,
                    preset=preset,
                )
                rows.append(
                    {
                        "input": str(file_path),
                        "output": str(out_file),
                        "status": "converted",
                        "message": "",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "input": str(file_path),
                        "output": str(out_file),
                        "status": "error",
                        "message": str(exc),
                    }
                )
        if report_path:
            _write_report(Path(report_path), rows)
        return

    if not in_img_path:
        raise ValueError("Single-file mode requires in_img_path")

    resolved_filename = filename or _default_name_for_single_input(in_img_path)
    if dry_run:
        planned = _prepare_output_path(out_img_path, resolved_filename, output_format)
        rows.append(
            {
                "input": in_img_path,
                "output": str(planned),
                "status": "planned",
                "message": "dry-run",
            }
        )
    else:
        out_file = squareify(
            in_img_path,
            target_size,
            out_img_path,
            resolved_filename,
            output_format=output_format,
            quality=quality,
            background=background,
            fit=fit,
            padding=padding,
            preset=preset,
        )
        rows.append(
            {"input": in_img_path, "output": str(out_file), "status": "converted", "message": ""}
        )
    if report_path:
        _write_report(Path(report_path), rows)


def main(
    in_img_path: Optional[str] = None,
    target_size: Optional[int] = 200,
    out_img_name: Optional[str] = None,
    filename: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Backward-compatible wrapper for existing integrations."""
    out_img_path = kwargs.get("out_img_path", out_img_name)
    process_images(
        in_img_path=in_img_path,
        in_dir=kwargs.get("in_dir"),
        target_size=target_size,
        out_img_path=out_img_path,
        filename=filename,
        output_format=kwargs.get("output_format", "webp"),
        quality=kwargs.get("quality", 95),
        background=kwargs.get("background", "auto"),
        overwrite=kwargs.get("overwrite", False),
        fit=kwargs.get("fit", "contain"),
        padding=kwargs.get("padding", 0.0),
        preset=kwargs.get("preset"),
        recursive=kwargs.get("recursive", False),
        include=kwargs.get("include"),
        exclude=kwargs.get("exclude"),
        dry_run=kwargs.get("dry_run", False),
        report_path=kwargs.get("report_path"),
    )


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Convert logos/images to square outputs.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--in_path", help="Path to a single input image.")
    input_group.add_argument("--in_dir", help="Path to an input directory for batch mode.")
    parser.add_argument(
        "--target_size",
        type=int,
        default=200,
        help="Target square size in pixels (default: 200).",
    )
    parser.add_argument("--out_path", required=True, help="Output directory path.")
    parser.add_argument(
        "--out_file_name",
        help="Output file base name (optional in single-file mode; defaults to input name).",
    )
    parser.add_argument(
        "--format",
        default="webp",
        help="Output format (examples: webp, png, jpeg, bmp, tiff, gif, ico).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="Image quality from 1-100 (default: 95).",
    )
    parser.add_argument(
        "--background",
        default="auto",
        help="Background fill: auto, black, white, or #RRGGBB (default: auto).",
    )
    parser.add_argument(
        "--fit",
        choices=["contain", "cover"],
        default="contain",
        help="Composition mode: contain (default) or cover.",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.0,
        help="Safe margin ratio from 0.0 to 0.45 used with contain mode.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        help="Apply common settings bundle (size/format/quality/fit/padding).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing outputs in batch mode.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Walk nested directories in batch mode.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Include glob pattern relative to input dir (repeatable).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude glob pattern relative to input dir (repeatable).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Preview conversion plan without writing output files.",
    )
    parser.add_argument(
        "--report_path",
        help="Optional conversion report path ending with .json or .csv.",
    )
    args = parser.parse_args()
    process_images(
        in_img_path=args.in_path,
        in_dir=args.in_dir,
        target_size=args.target_size,
        out_img_path=args.out_path,
        filename=args.out_file_name,
        output_format=args.format,
        quality=args.quality,
        background=args.background,
        overwrite=args.overwrite,
        fit=args.fit,
        padding=args.padding,
        preset=args.preset,
        recursive=args.recursive,
        include=args.include,
        exclude=args.exclude,
        dry_run=args.dry_run,
        report_path=args.report_path,
    )


if __name__ == "__main__":
    cli()
