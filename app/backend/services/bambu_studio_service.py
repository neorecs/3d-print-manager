import csv
import re
import shutil
import zipfile
from datetime import date
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Order, OrderItem, PrintBatch, PrintBatchItem, PrintJob, Product, ProductVariant


EXPORT_ROOT = Path("exports") / "PrintJobs"
UPLOAD_ROOT = Path("uploads")


def product_print_file_response(product: Product) -> FileResponse:
    source = resolve_product_print_file(product.print_file_path)
    return FileResponse(
        source,
        media_type="application/octet-stream",
        filename=download_filename(product, source),
        headers={"Cache-Control": "private, no-store"},
    )


def export_print_batch_for_bambu_studio(db: Session, batch: PrintBatch) -> dict:
    rows = build_batch_export_rows(db, batch)
    if not rows:
        raise HTTPException(status_code=400, detail="Batch bevat geen printtaken")

    export_date = (batch.planned_date or (batch.created_at.date() if batch.created_at else date.today())).isoformat()
    export_dir = EXPORT_ROOT / export_date / slugify(batch.batch_name)
    export_dir.mkdir(parents=True, exist_ok=True)

    printable_files = copy_batch_print_files(rows, export_dir / "printbestanden")
    production_csv = export_dir / "productielijst.csv"
    orders_csv = export_dir / "orderoverzicht.csv"
    markdown_file = export_dir / "LEESMIJ-BAMBU-STUDIO.md"
    archive_file = export_dir / f"{slugify(batch.batch_name)}-bambu-studio.zip"

    write_csv(production_csv, public_export_rows(rows))
    write_csv(
        orders_csv,
        [
            {
                "ordernummer": row["order_number"],
                "printtaak": row["job_id"],
                "sku": row["sku"],
                "product": row["product"],
                "variant": row["variant"],
                "aantal": row["quantity_in_batch"],
                "voor_order": row["quantity_to_order"],
                "voor_voorraad": row["quantity_to_inventory"],
            }
            for row in rows
        ],
    )
    markdown_file.write_text(build_batch_markdown(batch, rows, printable_files), encoding="utf-8")
    create_export_archive(archive_file, production_csv, orders_csv, markdown_file, printable_files)

    return {
        "status": "exported",
        "batch_id": batch.id,
        "export_dir": str(export_dir),
        "files": {
            "productielijst_csv": str(production_csv),
            "orderoverzicht_csv": str(orders_csv),
            "handleiding_markdown": str(markdown_file),
            "bambu_studio_zip": str(archive_file),
        },
        "download_url": f"/print-batches/{batch.id}/export/download",
        "row_count": len(rows),
        "print_file_count": len(printable_files),
        "missing_print_files": [row["product"] for row in rows if not row["print_file_available"]],
    }


def batch_export_download_response(db: Session, batch: PrintBatch) -> FileResponse:
    result = export_print_batch_for_bambu_studio(db, batch)
    archive = Path(result["files"]["bambu_studio_zip"])
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=archive.name,
        headers={"Cache-Control": "private, no-store"},
    )


def resolve_product_print_file(file_path: str | None) -> Path:
    if not file_path or not file_path.startswith("/uploads/product_print_files/"):
        raise HTTPException(status_code=404, detail="Aan dit product is geen printbestand gekoppeld")

    relative = Path(file_path.removeprefix("/uploads/"))
    source = (UPLOAD_ROOT / relative).resolve()
    allowed_root = (UPLOAD_ROOT / "product_print_files").resolve()
    if allowed_root not in source.parents or not source.is_file():
        raise HTTPException(status_code=404, detail="Het gekoppelde printbestand is niet gevonden in de opslag")
    return source


def download_filename(product: Product, source: Path) -> str:
    stored_name = re.sub(r"^[0-9a-f]{32}-", "", source.name, flags=re.IGNORECASE)
    product_name = slugify(product.internal_title or product.name)
    suffix = ".gcode.3mf" if stored_name.lower().endswith(".gcode.3mf") else source.suffix
    return f"{product_name}{suffix}"


def build_batch_export_rows(db: Session, batch: PrintBatch) -> list[dict]:
    batch_items = db.scalars(select(PrintBatchItem).where(PrintBatchItem.print_batch_id == batch.id)).all()
    rows = []
    for batch_item in batch_items:
        job = db.get(PrintJob, batch_item.print_job_id)
        if not job:
            continue
        product = db.get(Product, job.product_id)
        variant = db.get(ProductVariant, job.product_variant_id)
        order_item = db.get(OrderItem, job.order_item_id) if job.order_item_id else None
        order = db.get(Order, order_item.order_id) if order_item else None
        print_file_path = product.print_file_path if product and product.print_file_path else (variant.print_file_path if variant else None)
        print_file_available = False
        if print_file_path:
            try:
                resolve_product_print_file(print_file_path)
                print_file_available = True
            except HTTPException:
                pass
        rows.append(
            {
                "batch_id": batch.id,
                "batch_name": batch.batch_name,
                "job_id": job.id,
                "order_number": order.internal_order_number if order else "voorraadproductie",
                "product": product.name if product else "",
                "variant": variant.variant_name if variant else "",
                "sku": variant.sku if variant else "",
                "color": job.color or (variant.color if variant else ""),
                "material": job.material or (variant.material if variant else ""),
                "quantity_in_batch": batch_item.quantity_in_batch,
                "quantity_needed": job.quantity_needed,
                "quantity_planned": job.quantity_planned,
                "quantity_to_order": job.quantity_to_order,
                "quantity_to_inventory": job.quantity_to_inventory,
                "estimated_print_time_minutes": job.estimated_print_time_minutes,
                "estimated_filament_grams": job.estimated_filament_grams,
                "print_file": download_filename(product, Path(print_file_path)) if product and print_file_path else "",
                "print_file_available": print_file_available,
                "print_file_path": print_file_path or "",
            }
        )
    return sorted(rows, key=lambda row: (row["material"] or "", row["color"] or "", row["product"], row["variant"]))


def copy_batch_print_files(rows: list[dict], target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[Path, Path] = {}
    used_names: set[str] = set()
    for row in rows:
        if not row["print_file_available"]:
            continue
        source = resolve_product_print_file(row["print_file_path"])
        if source in copied:
            row["print_file"] = copied[source].name
            continue
        name = row["print_file"] or source.name
        candidate = name
        counter = 2
        while candidate.lower() in used_names:
            candidate = name.removesuffix(".gcode.3mf") + f"-{counter}.gcode.3mf"
            counter += 1
        destination = target_dir / candidate
        shutil.copy2(source, destination)
        copied[source] = destination
        used_names.add(candidate.lower())
        row["print_file"] = destination.name
    return list(copied.values())


def create_export_archive(archive: Path, production_csv: Path, orders_csv: Path, guide: Path, print_files: list[Path]) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(production_csv, production_csv.name)
        bundle.write(orders_csv, orders_csv.name)
        bundle.write(guide, guide.name)
        for print_file in print_files:
            bundle.write(print_file, f"printbestanden/{print_file.name}")


def public_export_rows(rows: list[dict]) -> list[dict]:
    return [
        {key: value for key, value in row.items() if key not in {"print_file_path", "print_file_available"}}
        for row in rows
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_batch_markdown(batch: PrintBatch, rows: list[dict], print_files: list[Path]) -> str:
    missing = [row for row in rows if not row["print_file_available"]]
    lines = [
        f"# Bambu Studio pakket - {batch.batch_name}",
        "",
        "## Zo start je de prints",
        "",
        "1. Open de map `printbestanden`.",
        "2. Open het gewenste `.gcode.3mf` bestand in Bambu Studio.",
        "3. Controleer printer, plate, materiaal/kleur en AMS-toewijzing.",
        "4. Kies in Bambu Studio `Print plate` om via Bambu Cloud of je lokale verbinding te starten.",
        "5. Verwerk na afloop het resultaat in 3D Print Manager.",
        "",
        f"- Materiaal: {batch.material or '-'}",
        f"- Kleur: {batch.color or '-'}",
        f"- Geschatte printtijd: {batch.estimated_total_print_time_minutes or 0} minuten",
        f"- Geschat filament: {batch.estimated_total_filament_grams or 0} gram",
        f"- Meegeleverde unieke printbestanden: {len(print_files)}",
        "",
        "## Productielijst",
        "",
    ]
    for row in rows:
        lines.append(
            f"- {row['quantity_in_batch']}x {row['product']} / {row['variant']} ({row['sku']}) - "
            f"{row['material'] or '-'} / {row['color'] or '-'} - order: {row['order_number']} - "
            f"bestand: {row['print_file'] or 'ONTBREEKT'}"
        )
    if missing:
        lines.extend(["", "## Let op", "", "Voor deze regels ontbreekt een bruikbaar printbestand:"])
        lines.extend(f"- {row['product']} / {row['variant']}" for row in missing)
    lines.append("")
    return "\n".join(lines)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return value.strip("-") or "print"
