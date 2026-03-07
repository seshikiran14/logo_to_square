from pathlib import Path

import pytest
from PIL import Image

from logo_to_square.square_img_using_PIL import cli, main, process_images, squareify


def _create_opaque_image(path: Path, size=(120, 80), color=(200, 30, 30)) -> None:
    Image.new("RGB", size, color).save(path)


def _create_transparent_image(path: Path, size=(120, 80)) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(30, 90):
        for y in range(20, 60):
            image.putpixel((x, y), (255, 0, 0, 255))
    image.save(path)


def _create_transparent_white_logo(path: Path, size=(120, 80)) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(30, 90):
        for y in range(20, 60):
            image.putpixel((x, y), (255, 255, 255, 255))
    image.save(path)


def _create_transparent_black_logo(path: Path, size=(120, 80)) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(30, 90):
        for y in range(20, 60):
            image.putpixel((x, y), (0, 0, 0, 255))
    image.save(path)


def test_squareify_creates_square_output_for_opaque_image(tmp_path):
    source = tmp_path / "opaque.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    out_file = squareify(source, 128, output_dir, "opaque")

    assert out_file.exists()
    with Image.open(out_file) as out_image:
        assert out_image.size == (128, 128)


def test_squareify_respects_background_override_for_transparent_image(tmp_path):
    source = tmp_path / "transparent.png"
    output_dir = tmp_path / "out"
    _create_transparent_image(source)

    out_file = squareify(source, 96, output_dir, "transparent", background="white")

    assert out_file.exists()
    with Image.open(out_file) as out_image:
        assert out_image.size == (96, 96)
        rgb_image = out_image.convert("RGB")
        assert rgb_image.getpixel((0, 0)) == (255, 255, 255)


def test_squareify_handles_fully_transparent_input_with_auto_background(tmp_path):
    source = tmp_path / "fully_transparent.png"
    output_dir = tmp_path / "out"
    Image.new("RGBA", (80, 40), (0, 0, 0, 0)).save(source)

    out_file = squareify(source, 120, output_dir, "fully_transparent", background="auto")

    assert out_file.exists()
    with Image.open(out_file) as out_image:
        assert out_image.size == (120, 120)


def test_squareify_auto_background_uses_contrast_for_white_foreground(tmp_path):
    source = tmp_path / "transparent_white_logo.png"
    output_dir = tmp_path / "out"
    _create_transparent_white_logo(source)

    out_file = squareify(source, 120, output_dir, "white_logo_auto_bg", background="auto")

    with Image.open(out_file) as out_image:
        assert out_image.size == (120, 120)
        rgb_image = out_image.convert("RGB")
        assert rgb_image.getpixel((0, 0)) == (0, 0, 0)


def test_squareify_auto_background_uses_contrast_for_black_foreground(tmp_path):
    source = tmp_path / "transparent_black_logo.png"
    output_dir = tmp_path / "out"
    _create_transparent_black_logo(source)

    out_file = squareify(source, 120, output_dir, "black_logo_auto_bg", background="auto")

    with Image.open(out_file) as out_image:
        assert out_image.size == (120, 120)
        rgb_image = out_image.convert("RGB")
        assert rgb_image.getpixel((0, 0)) == (255, 255, 255)


def test_squareify_handles_tiny_images(tmp_path):
    source = tmp_path / "tiny.png"
    output_dir = tmp_path / "out"
    Image.new("RGB", (3, 2), (10, 20, 30)).save(source)

    out_file = squareify(source, 64, output_dir, "tiny")

    assert out_file.exists()
    with Image.open(out_file) as out_image:
        assert out_image.size == (64, 64)


def test_squareify_supports_png_output(tmp_path):
    source = tmp_path / "opaque.jpg"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    out_file = squareify(
        source,
        72,
        output_dir,
        "opaque_png",
        output_format="png",
        background="#112233",
    )

    assert out_file.suffix == ".png"
    with Image.open(out_file) as out_image:
        assert out_image.size == (72, 72)


def test_squareify_supports_bmp_output(tmp_path):
    source = tmp_path / "opaque.jpg"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    out_file = squareify(source, 64, output_dir, "opaque_bmp", output_format="bmp")

    assert out_file.suffix == ".bmp"
    with Image.open(out_file) as out_image:
        assert out_image.size == (64, 64)


def test_squareify_cover_mode(tmp_path):
    source = tmp_path / "wide.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source, size=(200, 80), color=(100, 100, 220))

    out_file = squareify(source, 100, output_dir, "wide_cover", fit="cover")

    with Image.open(out_file) as out_image:
        assert out_image.size == (100, 100)


def test_squareify_no_upscale_keeps_small_logo_size(tmp_path):
    source = tmp_path / "small_logo.png"
    output_dir = tmp_path / "out"
    Image.new("RGB", (20, 10), (10, 20, 30)).save(source)

    out_file = squareify(
        source,
        100,
        output_dir,
        "small_logo",
        output_format="png",
        background="#ffffff",
        upscale=False,
    )

    with Image.open(out_file) as out_image:
        assert out_image.size == (100, 100)
        bbox = out_image.convert("RGB").point(lambda px: 0 if px == 255 else 255).getbbox()
        assert bbox is not None
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        assert width == 20
        assert height == 10


def test_squareify_preset_app_icon(tmp_path):
    source = tmp_path / "logo.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source, size=(160, 80))

    out_file = squareify(source, None, output_dir, "preset_logo", preset="app-icon")

    assert out_file.suffix == ".png"
    with Image.open(out_file) as out_image:
        assert out_image.size == (512, 512)


def test_cli_batch_mode_creates_outputs(tmp_path, monkeypatch):
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir()
    _create_opaque_image(input_dir / "one.png")
    _create_opaque_image(input_dir / "two.jpg")

    monkeypatch.setattr(
        "sys.argv",
        [
            "logo-to-square",
            "--in_dir",
            str(input_dir),
            "--out_path",
            str(output_dir),
            "--target_size",
            "80",
            "--format",
            "webp",
            "--overwrite",
        ],
    )

    cli()

    assert (output_dir / "one_square.webp").exists()
    assert (output_dir / "two_square.webp").exists()


def test_process_images_recursive_dry_run_with_report(tmp_path):
    input_dir = tmp_path / "inputs"
    nested = input_dir / "nested"
    nested.mkdir(parents=True)
    output_dir = tmp_path / "outputs"
    report = tmp_path / "report.json"
    _create_opaque_image(nested / "one.png")
    _create_opaque_image(nested / "two.jpg")

    process_images(
        in_img_path=None,
        in_dir=str(input_dir),
        target_size=80,
        out_img_path=str(output_dir),
        filename=None,
        output_format="webp",
        quality=90,
        background="auto",
        overwrite=False,
        recursive=True,
        include=["nested/*.png"],
        exclude=[],
        dry_run=True,
        report_path=str(report),
    )

    assert not (output_dir / "nested" / "one_square.webp").exists()
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "planned" in content
    assert "one_square.webp" in content
    assert "two_square.webp" not in content


def test_main_legacy_signature_still_works(tmp_path):
    source = tmp_path / "legacy.png"
    output_dir = tmp_path / "legacy_out"
    _create_opaque_image(source)

    main(str(source), 90, str(output_dir), "legacy_name")

    out_file = output_dir / "legacy_name_square.webp"
    assert out_file.exists()


def test_squareify_invalid_background_raises_value_error(tmp_path):
    source = tmp_path / "opaque.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    with pytest.raises(ValueError, match="background must be one of"):
        squareify(source, 128, output_dir, "opaque_bad_bg", background="pink")


def test_squareify_missing_input_raises_file_not_found(tmp_path):
    output_dir = tmp_path / "out"

    with pytest.raises(FileNotFoundError, match="Input image not found"):
        squareify(tmp_path / "missing.png", 128, output_dir, "missing")


def test_squareify_invalid_upscale_flag_raises_value_error(tmp_path):
    source = tmp_path / "opaque.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    with pytest.raises(ValueError, match="upscale must be a boolean value"):
        squareify(source, 128, output_dir, "bad_upscale", upscale="no")


def test_squareify_invalid_output_format_raises_value_error(tmp_path):
    source = tmp_path / "opaque.png"
    output_dir = tmp_path / "out"
    _create_opaque_image(source)

    with pytest.raises(ValueError, match="Unsupported output format"):
        squareify(source, 128, output_dir, "bad_format", output_format="svg")


def test_process_images_invalid_report_extension_raises_value_error(tmp_path):
    source = tmp_path / "opaque.png"
    output_dir = tmp_path / "out"
    report = tmp_path / "report.txt"
    _create_opaque_image(source)

    with pytest.raises(ValueError, match="report_path must end with"):
        process_images(
            in_img_path=str(source),
            in_dir=None,
            target_size=80,
            out_img_path=str(output_dir),
            filename="opaque",
            output_format="webp",
            quality=90,
            background="auto",
            overwrite=False,
            report_path=str(report),
        )
