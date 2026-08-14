import csv
import json
import math
import re
import shutil
import tempfile
import zipfile
from copy import copy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import BambuPrinter, Order, OrderItem, PrintBatch, PrintBatchItem, PrintJob, Product, ProductVariant


EXPORT_ROOT = Path("exports") / "PrintJobs"
UPLOAD_ROOT = Path("uploads")
PREPARED_ROOT = UPLOAD_ROOT / "prepared_bambu_files"

COLOR_NAMES = {
    "zwart": "#000000",
    "black": "#000000",
    "wit": "#FFFFFF",
    "white": "#FFFFFF",
    "rood": "#FF0000",
    "red": "#FF0000",
    "groen": "#00A651",
    "green": "#00A651",
    "blauw": "#0066CC",
    "blue": "#0066CC",
    "geel": "#FFD400",
    "yellow": "#FFD400",
    "oranje": "#FF7A00",
    "orange": "#FF7A00",
    "paars": "#800080",
    "purple": "#800080",
    "roze": "#FF69B4",
    "pink": "#FF69B4",
    "grijs": "#808080",
    "gray": "#808080",
    "grey": "#808080",
    "bruin": "#8B4513",
    "brown": "#8B4513",
}


def product_print_file_response(product: Product) -> FileResponse:
    source = resolve_product_print_file(product.print_file_path)
    return FileResponse(
        source,
        media_type="application/octet-stream",
        filename=download_filename(product, source),
        headers={"Cache-Control": "private, no-store"},
    )


def product_print_preparation(db: Session, product: Product, variant: ProductVariant, printer: BambuPrinter) -> dict:
    if variant.product_id != product.id:
        raise HTTPException(status_code=400, detail="De gekozen variant hoort niet bij dit product")
    metadata = inspect_product_print_file(product)
    required_material = _normalize_material(variant.material)
    sliced_material = _normalize_material(metadata.get("filament_material"))
    warnings: list[str] = []
    if not required_material:
        warnings.append("De variant heeft geen materiaal. Kies de filamentrol handmatig in Bambu Studio.")
    if required_material and sliced_material and sliced_material != required_material:
        raise HTTPException(
            status_code=409,
            detail=f"Dit bestand is geslicet voor {metadata['filament_material']}, maar de variant vraagt {variant.material}. Slice het bestand opnieuw met het juiste materiaal.",
        )

    file_model = _normalize_printer_model(metadata.get("printer_model"))
    selected_model = _normalize_printer_model(printer.model)
    if file_model and selected_model and file_model not in selected_model and selected_model not in file_model:
        raise HTTPException(
            status_code=409,
            detail=f"Dit bestand is geslicet voor {metadata['printer_model']}, niet voor {printer.model}. Kies een compatibele printer of slice opnieuw.",
        )

    slots = _printer_ams_slots(printer)
    material_slots = [slot for slot in slots if _normalize_material(slot.get("material")) == required_material]
    if not material_slots:
        warnings.append(
            f"Op {printer.name} is geen passende AMS-rol gevonden. Kies of plaats het filament handmatig in Bambu Studio."
        )
        ranked = []
        recommended = None
    else:
        requested_color = _parse_color(variant.color)
        ranked = sorted(material_slots, key=lambda slot: _color_distance(requested_color, _parse_color(slot.get("color_hex"))))
        recommended = ranked[0]
        if requested_color is not None and _color_distance(requested_color, _parse_color(recommended.get("color_hex"))) > 140:
            recommended = None
            warnings.append(
                f"Op {printer.name} is wel {variant.material} aanwezig, maar niet in de gevraagde kleur {variant.color}. Kies de rol handmatig in Bambu Studio."
            )
    return {
        "product_id": product.id,
        "variant_id": variant.id,
        "printer_id": printer.id,
        "printer_name": printer.name,
        "printer_model": printer.model,
        "file_printer_model": metadata.get("printer_model"),
        "material": variant.material,
        "color": variant.color,
        "file_material": metadata.get("filament_material"),
        "recommended_slot": recommended,
        "compatible_slots": ranked,
        "color_distance": (
            _color_distance(_parse_color(variant.color), _parse_color(recommended.get("color_hex")))
            if recommended and _parse_color(variant.color) is not None
            else None
        ),
        "warnings": warnings,
    }


def prepared_product_print_file_response(
    db: Session,
    product: Product,
    variant: ProductVariant,
    printer: BambuPrinter,
    ams_id: int,
    tray_id: int,
    background_tasks: BackgroundTasks,
) -> FileResponse:
    preparation = product_print_preparation(db, product, variant, printer)
    if ams_id < 0 or tray_id < 0:
        return product_print_file_response(product)
    slot = next(
        (
            item
            for item in preparation["compatible_slots"]
            if int(item["ams_id"]) == ams_id and int(item["tray_id"]) == tray_id
        ),
        None,
    )
    if not slot:
        raise HTTPException(status_code=409, detail="De gekozen AMS-sleuf bevat niet het juiste materiaal")

    source = resolve_product_print_file(product.print_file_path)
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix="prepared-", suffix=".gcode.3mf", dir=PREPARED_ROOT, delete=False)
    target = Path(handle.name)
    handle.close()
    try:
        _write_prepared_3mf(source, target, slot)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    background_tasks.add_task(target.unlink, missing_ok=True)
    return FileResponse(
        target,
        media_type="application/octet-stream",
        filename=download_filename(product, source),
        headers={"Cache-Control": "private, no-store"},
        background=background_tasks,
    )


def inspect_product_print_file(product: Product) -> dict:
    source = resolve_product_print_file(product.print_file_path)
    try:
        with zipfile.ZipFile(source, "r") as archive:
            project = json.loads(archive.read("Metadata/project_settings.config"))
            slice_root = ElementTree.fromstring(archive.read("Metadata/slice_info.config"))
    except (KeyError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise HTTPException(status_code=409, detail=f"Het gekoppelde 3MF-bestand kan niet worden gecontroleerd: {exc}") from exc
    filament = slice_root.find(".//filament[@id='1']")
    if filament is None:
        filament = slice_root.find(".//filament")
    plate = slice_root.find(".//plate")
    printer_model_id = None
    if plate is not None:
        model_item = plate.find("./metadata[@key='printer_model_id']")
        printer_model_id = model_item.get("value") if model_item is not None else None
    return {
        "printer_model": project.get("printer_model") or project.get("printer_settings_id") or printer_model_id,
        "printer_model_id": printer_model_id,
        "nozzle_diameter": project.get("nozzle_diameter"),
        "filament_material": filament.get("type") if filament is not None else None,
        "filament_color": _format_hex_color(filament.get("color")) if filament is not None else None,
    }


def _write_prepared_3mf(source: Path, target: Path, slot: dict) -> None:
    color = _format_hex_color(slot.get("color_hex"))
    material = str(slot.get("material") or "").strip()
    if not color or not material:
        raise HTTPException(status_code=409, detail="De gekozen AMS-sleuf heeft geen bruikbare materiaal- en kleurgegevens")
    with zipfile.ZipFile(source, "r") as source_zip, zipfile.ZipFile(target, "w") as target_zip:
        for info in source_zip.infolist():
            data = source_zip.read(info.filename)
            if info.filename == "Metadata/slice_info.config":
                root = ElementTree.fromstring(data)
                filament = root.find(".//filament[@id='1']")
                if filament is None:
                    filament = root.find(".//filament")
                if filament is not None:
                    filament.set("color", color)
                data = ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)
            elif info.filename == "Metadata/plate_1.json":
                plate = json.loads(data)
                colors = plate.get("filament_colors") if isinstance(plate.get("filament_colors"), list) else []
                plate["filament_colors"] = [color, *colors[1:]] if colors else [color]
                data = json.dumps(plate, separators=(",", ":")).encode("utf-8")
            elif info.filename == "Metadata/project_settings.config":
                settings = json.loads(data)
                colors = settings.get("filament_colour") if isinstance(settings.get("filament_colour"), list) else []
                settings["filament_colour"] = [color, *colors[1:]] if colors else [color]
                data = json.dumps(settings, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            copied = copy(info)
            target_zip.writestr(copied, data)


def _printer_ams_slots(printer: BambuPrinter) -> list[dict]:
    try:
        value = json.loads(printer.ams_slots_json or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def _normalize_material(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _normalize_printer_model(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper().replace("BAMBU LAB", ""))


def _format_hex_color(value: object) -> str | None:
    text = str(value or "").strip().lstrip("#")
    if len(text) == 8:
        text = text[:6]
    if len(text) != 6 or any(char not in "0123456789ABCDEFabcdef" for char in text):
        return None
    return f"#{text.upper()}"


def _parse_color(value: object) -> tuple[int, int, int] | None:
    text = str(value or "").strip().lower()
    color = _format_hex_color(COLOR_NAMES.get(text, text))
    if not color:
        return None
    return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))


def _color_distance(left: tuple[int, int, int] | None, right: tuple[int, int, int] | None) -> float:
    if left is None or right is None:
        return math.inf
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


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
