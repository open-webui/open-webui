import csv

from open_webui.internal.db import get_db
from open_webui.models.charities import Charity


def import_from_csv(path):
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        with get_db() as db:
            charities = []
            for row in reader:
                charity_id = row.get("Charity ID", "").strip()
                name = row.get("Name", "").strip().title()
                website = row.get("Website", "").strip()
                email = row.get("Email", "").strip()
                if not charity_id or not name:
                    print(f"Skipping row with missing charity_id or name: {row}")
                charity = Charity(
                    name=name,
                    charity_id=charity_id,
                    website=website,
                    email=email,
                    is_imported=True,
                )
                charities.append(charity)
    db.add_all(charities)
    db.commit()
    print("Import complete.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python import_charities.py /path/to/file.csv")
        exit(1)
    import_from_csv(sys.argv[1])
