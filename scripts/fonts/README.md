
Place a Georgian-capable TTF here so host-side post-processing can render Georgian text.

Preferred font: Noto Sans Georgian Bold (NotoSansGeorgian-Bold.ttf).

Recommendation: commit the Bold TTF to the repo at `scripts/fonts/NotoSansGeorgian-Bold.ttf` (preferred for Docker/Prod reproducibility and deterministic rendering).

Alternatively, run the downloader to fetch the TTF at build time (less preferred for the "commit into repo" requirement):

```bash
bash scripts/download_noto_georgian.sh
```

If you commit the font file, ensure it is placed exactly at `scripts/fonts/NotoSansGeorgian-Bold.ttf`.
