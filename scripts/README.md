# Host-side Georgian text overlay

This folder contains a small helper script to post-process generated images by overlaying Georgian text using a font that supports Georgian (for example, `NotoSansGeorgian-Regular.ttf`).

Quick steps:

1. Install dependencies:

```bash
python -m pip install -r scripts/requirements.txt
```

2. Preferred: commit the TTF into the repo at `scripts/fonts/NotoSansGeorgian-Regular.ttf` so Docker/Prod builds are reproducible.

Alternatively, you can run the downloader which will attempt to fetch the TTF into `scripts/fonts/` (network required):

```bash
bash scripts/download_noto_georgian.sh
```

3. Run the script (if the font is placed at `scripts/fonts/NotoSansGeorgian-Bold.ttf`, you can omit `--font`):

```bash
# On Unix/macOS (shell handles UTF-8 fine):
python scripts/overlay_georgian_text.py \
  --input path/to/input.png \
  --output path/to/output.png \
  --text "ქართული ტექსტი" \
  --size 72 --color "#FFFFFF" --stroke 2

# On Windows/PowerShell it's safer to put the text into a UTF-8 file and use --text-file:
python scripts/overlay_georgian_text.py \
  --input path/to/input.png \
  --output path/to/output.png \
  --text-file path/to/text.txt \
  --size 72 --color "#FFFFFF" --stroke 2
```

PowerShell note: if passing text on the command line, ensure UTF-8 is enabled (`chcp 65001`) and `PYTHONIOENCODING=utf-8` is set. Using `--text-file` avoids these issues.

Notes:
- The script requires an explicit font path. If you omit the font or it doesn't support Georgian, the characters will not render correctly.
- Use `--x` and `--y` to position text in pixels, otherwise use `--anchor` (default `mm` center).
