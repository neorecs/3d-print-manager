from pathlib import Path

from database import SessionLocal
from models import Product


with SessionLocal() as db:
    db.add(Product(name="Recovery test product", internal_title="Recovery test product", status="concept", active=True))
    db.commit()

upload = Path("uploads/recovery/product.txt")
upload.parent.mkdir(parents=True, exist_ok=True)
upload.write_text("recovery-upload-content\n", encoding="utf-8")
print("Hersteltestdata en uploadbestand aangemaakt.")
