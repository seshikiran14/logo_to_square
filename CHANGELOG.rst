=========
Changelog
=========

Unreleased
==========

- Improved image conversion robustness with safer path handling, validation, and
  explicit error messages for invalid input/corrupt images.
- Added configurable output options (format, quality, background) and batch
  directory processing with overwrite control.
- Upgraded resize quality and tiny-image corner sampling to avoid index errors
  in background color detection.
- Added CLI entry point (``logo-to-square``), practical README usage docs, and
  pytest coverage for single image, batch mode, transparent backgrounds, and
  tiny images.
- Kept backwards compatibility for ``main(...)`` integrations while introducing
  a clearer internal ``process_images(...)`` flow.

Version 0.1
===========

- Feature A added
- FIX: nasty bug #1729 fixed
- add your changes here!
