"""Copy the BatchTechUI brand files (batchtech/assets/brand/) over Open WebUI's icons and splash images."""

import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
brand = root / 'batchtech/assets/brand'
for f in sorted(brand.iterdir()):
    shutil.copyfile(f, root / 'static/static' / f.name)
shutil.copyfile(brand / 'favicon.png', root / 'static/favicon.png')
print('assets written')
