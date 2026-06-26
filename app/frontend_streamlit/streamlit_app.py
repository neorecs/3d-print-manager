import os
import re
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CURRENT_FILE = Path(__file__).resolve()
FRONTEND_ROOT = CURRENT_FILE.parent
APP_ROOT = CURRENT_FILE.parents[2] if len(CURRENT_FILE.parents) >= 3 else FRONTEND_ROOT
UI_GUIDE_PATHS = [
    FRONTEND_ROOT / "UI_HANDLEIDING.md",
    APP_ROOT / "docs" / "UI_HANDLEIDING.md",
]


st.set_page_config(page_title="3D Print Manager", layout="wide")


st.markdown(
    """
    <style>
    :root {
        --pm-border: #d9e2e7;
        --pm-muted: #5d6b72;
        --pm-panel: #ffffff;
        --pm-soft: #f5f8fa;
        --pm-accent: #0f766e;
        --pm-accent-soft: #d9f3ef;
        --pm-warn: #b45309;
        --pm-warn-soft: #fff4d6;
        --pm-danger: #b42318;
        --pm-danger-soft: #ffe4e0;
    }

    .block-container {
        padding-top: 1.3rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stSidebar"] {
        background: #f8fafb;
        border-right: 1px solid var(--pm-border);
    }

    .pm-page-title {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .pm-page-title h1 {
        font-size: 2rem;
        line-height: 1.15;
        margin: 0;
        letter-spacing: 0;
    }

    .pm-page-title p {
        margin: .35rem 0 0;
        color: var(--pm-muted);
        max-width: 760px;
    }

    .pm-card {
        border: 1px solid var(--pm-border);
        background: var(--pm-panel);
        border-radius: 8px;
        padding: 1rem;
        min-height: 118px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .05);
    }

    .pm-card-title {
        color: var(--pm-muted);
        font-size: .82rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: .45rem;
    }

    .pm-card-value {
        color: #152026;
        font-size: 2rem;
        line-height: 1;
        font-weight: 750;
        letter-spacing: 0;
    }

    .pm-card-note {
        color: var(--pm-muted);
        font-size: .9rem;
        margin-top: .45rem;
    }

    .pm-section {
        border: 1px solid var(--pm-border);
        border-radius: 8px;
        padding: 1rem;
        background: #ffffff;
        margin: .5rem 0 1rem;
        color: #152026;
    }

    .pm-section h3 {
        font-size: 1rem;
        margin: 0 0 .75rem;
        letter-spacing: 0;
        color: #152026;
        font-weight: 750;
    }

    .pm-section p {
        color: #33444c;
        font-size: .88rem;
        margin: -.35rem 0 .85rem;
    }

    .pm-list-card {
        border: 1px solid var(--pm-border);
        border-radius: 8px;
        background: #ffffff;
        padding: .9rem;
        margin-bottom: .75rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    }

    .pm-list-card-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: .75rem;
        margin-bottom: .7rem;
    }

    .pm-list-card-title {
        font-weight: 750;
        font-size: 1rem;
        color: #152026;
    }

    .pm-list-card-subtitle {
        color: var(--pm-muted);
        font-size: .88rem;
        margin-top: .15rem;
    }

    .pm-detail-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .55rem .85rem;
    }

    .pm-detail-grid span {
        color: var(--pm-muted);
        font-size: .84rem;
    }

    .pm-detail-grid strong {
        display: block;
        color: #26343b;
        font-size: .78rem;
        text-transform: uppercase;
        margin-bottom: .08rem;
    }

    .pm-work-hint {
        border-left: 4px solid var(--pm-accent);
        background: #edf8f6;
        border-radius: 8px;
        padding: .75rem .9rem;
        color: #18413d;
        margin: .5rem 0 1rem;
    }

    .pm-purpose {
        border: 1px solid var(--pm-border);
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        margin: .4rem 0 1rem;
    }

    .pm-purpose h2 {
        font-size: 1.05rem;
        margin: 0 0 .7rem;
        letter-spacing: 0;
        color: #152026;
    }

    .pm-purpose-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .75rem;
    }

    .pm-purpose-item {
        border-left: 3px solid var(--pm-accent);
        background: #f5f8fa;
        border-radius: 8px;
        padding: .75rem;
        min-height: 86px;
    }

    .pm-purpose-item strong {
        display: block;
        font-size: .9rem;
        margin-bottom: .25rem;
        color: #152026;
    }

    .pm-purpose-item span {
        color: #33444c;
        font-size: .86rem;
    }

    @media (max-width: 900px) {
        .pm-page-title {
            display: block;
        }

        .pm-detail-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    .pm-status {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: .2rem .55rem;
        font-size: .8rem;
        font-weight: 700;
        border: 1px solid var(--pm-border);
        background: var(--pm-soft);
        color: #24343b;
    }

    .pm-status.good {
        background: var(--pm-accent-soft);
        color: #115e59;
        border-color: #99ded3;
    }

    .pm-status.warn {
        background: var(--pm-warn-soft);
        color: var(--pm-warn);
        border-color: #f5d48a;
    }

    .pm-status.danger {
        background: var(--pm-danger-soft);
        color: var(--pm-danger);
        border-color: #ffb4ab;
    }

    .pm-workflow {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: .5rem;
        margin: .75rem 0 1rem;
    }

    .pm-step {
        border: 1px solid var(--pm-border);
        border-radius: 8px;
        padding: .75rem;
        background: #f5f8fa;
        min-height: 74px;
    }

    .pm-step strong {
        display: block;
        font-size: .9rem;
        margin-bottom: .25rem;
        color: #152026;
    }

    .pm-step span {
        color: #33444c;
        font-size: .82rem;
    }

    @media (max-width: 900px) {
        .pm-page-title {
            display: block;
        }
        .pm-workflow {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .pm-purpose-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any] | None = None) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def api_upload(path: str, uploaded_file: Any, data: dict[str, Any]) -> Any:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    response = requests.post(f"{API_BASE_URL}{path}", files=files, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def api_put(path: str, payload: dict[str, Any]) -> Any:
    response = requests.put(f"{API_BASE_URL}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def api_delete(path: str) -> Any:
    response = requests.delete(f"{API_BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in ("", None)}


def uploaded_media_bytes(file_path: str | None) -> bytes | None:
    if not file_path or not file_path.startswith("/uploads/"):
        return None
    try:
        response = requests.get(f"{API_BASE_URL}{file_path}", timeout=10)
        response.raise_for_status()
        return response.content
    except Exception:
        return None


def product_name(products: list[dict[str, Any]], product_id: int) -> str:
    return next(product["name"] for product in products if product["id"] == product_id)


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "product"


def split_words(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;\n]+", value or "") if item.strip()]


def readable_words(value: str) -> list[str]:
    stop_words = {
        "aan",
        "als",
        "bij",
        "de",
        "een",
        "en",
        "het",
        "in",
        "is",
        "met",
        "of",
        "op",
        "te",
        "voor",
        "van",
        "wat",
        "die",
        "dat",
        "this",
        "the",
        "and",
        "for",
        "with",
    }
    words = re.findall(r"[a-zA-Z0-9À-ÿ]+", value.lower())
    return [word for word in words if len(word) > 2 and word not in stop_words]


def unique_values(values: list[str], limit: int | None = None) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        cleaned = value.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(value.strip())
        if limit and len(unique) >= limit:
            break
    return unique


def suggest_product_tags(
    *,
    idea: str,
    audience: str,
    style: str,
    material: str,
    colors: list[str],
    product_type: str,
    category: str,
    extra_keywords: str,
) -> list[str]:
    tag_candidates: list[str] = []
    tag_candidates.extend([idea, product_type, category, material])
    tag_candidates.extend(colors)

    for source in [idea, audience, style, product_type, category]:
        tag_candidates.extend(readable_words(source))

    material_lower = material.strip().lower()
    if material_lower:
        tag_candidates.append(f"3d print {material_lower}")

    for color in colors:
        if color.strip() and idea.strip():
            tag_candidates.append(f"{idea.strip()} {color.strip()}")

    if category.strip():
        tag_candidates.append(f"3d geprint {category.strip().lower()}")
    else:
        tag_candidates.append("3d geprint")

    tag_candidates.extend(split_words(extra_keywords))
    return unique_values(tag_candidates, limit=12)


def page_header(title: str, subtitle: str | None = None, status: str | None = None) -> None:
    status_html = f"<span class='pm-status good'>{status}</span>" if status else ""
    st.markdown(
        f"""
        <div class="pm-page-title">
            <div>
                <h1>{title}</h1>
                <p>{subtitle or ""}</p>
            </div>
            <div>{status_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="pm-card">
            <div class="pm-card-title">{label}</div>
            <div class="pm-card-value">{value}</div>
            <div class="pm-card-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_start(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<div class='pm-section'><h3>{title}</h3>{subtitle_html}", unsafe_allow_html=True)


def section_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def status_class(status: str | None) -> str:
    if status in {"gepubliceerd", "volledig_uit_voorraad", "verwerkt", "geprint", "geaccepteerd"}:
        return "good"
    if status in {"deels_te_printen", "synchronisatie_nodig", "laag", "nieuw", "gepland"}:
        return "warn"
    if status in {"fout", "volledig_te_printen", "mislukt", "geannuleerd"}:
        return "danger"
    return ""


def status_badge(status: str | None) -> str:
    label = status or "-"
    return f"<span class='pm-status {status_class(status)}'>{label.replace('_', ' ')}</span>"


def safe_text(value: Any) -> str:
    if value in (None, ""):
        return "-"
    return escape(str(value))


def record_card(
    title: Any,
    subtitle: Any = None,
    status: Any = None,
    details: list[tuple[str, Any]] | None = None,
) -> None:
    detail_html = ""
    if details:
        detail_html = "<div class=\"pm-detail-grid\">" + "".join(
            f"<span><strong>{escape(label)}</strong>{safe_text(value)}</span>" for label, value in details
        ) + "</div>"
    st.markdown(
        f"""
        <div class="pm-list-card">
            <div class="pm-list-card-head">
                <div>
                    <div class="pm-list-card-title">{safe_text(title)}</div>
                    <div class="pm-list-card-subtitle">{safe_text(subtitle)}</div>
                </div>
                {status_badge(str(status)) if status is not None else ""}
            </div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def work_hint(text: str) -> None:
    st.markdown(f'<div class="pm-work-hint">{escape(text)}</div>', unsafe_allow_html=True)


def workflow_steps(title: str, steps: list[tuple[str, str]]) -> None:
    st.subheader(title)
    st.markdown(
        "<div class='pm-workflow'>"
        + "".join(
            f"<div class='pm-step'><strong>{escape(step_title)}</strong><span>{escape(step_text)}</span></div>"
            for step_title, step_text in steps
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def screen_purpose(items: list[tuple[str, str]]) -> None:
    st.markdown(
        """
        <div class="pm-purpose">
            <h2>Wat doe ik hier?</h2>
            <div class="pm-purpose-grid">
        """
        + "".join(
            f"<div class='pm-purpose-item'><strong>{escape(title)}</strong><span>{escape(text)}</span></div>"
            for title, text in items
        )
        + """
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_by_status(records: list[dict[str, Any]], widget_key: str) -> list[dict[str, Any]]:
    statuses = sorted({str(record.get("status") or "-") for record in records})
    choice = st.selectbox("Statusfilter", ["Alle"] + statuses, key=widget_key)
    if choice == "Alle":
        return records
    return [record for record in records if str(record.get("status") or "-") == choice]


def normalized_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("items", [data])
    return data or []


COLUMN_LABELS = {
    "id": "ID",
    "product_id": "Product",
    "product_variant_id": "Variant",
    "product": "Product",
    "variant": "Variant",
    "platform_id": "Platform",
    "platform": "Platform",
    "publication_status": "Publicatiestatus",
    "inventory_status": "Voorraadstatus",
    "internal_order_number": "Ordernummer",
    "external_order_id": "Extern ordernummer",
    "customer_name": "Klant",
    "customer_email": "E-mail",
    "order_date": "Orderdatum",
    "total_amount": "Totaal",
    "currency": "Valuta",
    "status": "Status",
    "quantity_ordered": "Besteld",
    "quantity_from_inventory": "Uit voorraad",
    "quantity_to_print": "Te printen",
    "unit_sale_price": "Stukprijs",
    "quantity_on_hand": "Op voorraad",
    "quantity_reserved": "Gereserveerd",
    "free_stock": "Vrije voorraad",
    "minimum_stock_level": "Minimum",
    "movement_type": "Beweging",
    "created_at": "Aangemaakt",
    "updated_at": "Bijgewerkt",
    "last_synced_at": "Laatste sync",
    "last_error": "Laatste fout",
    "external_product_id": "Extern product-ID",
    "external_listing_id": "Externe listing",
    "platform_title": "Platformtitel",
    "platform_description": "Platformomschrijving",
    "platform_category": "Platformcategorie",
    "platform_tags": "Platformtags",
    "platform_price_override": "Platformprijs",
    "color": "Kleur",
    "material": "Materiaal",
    "variant_name": "Variantnaam",
    "sku": "SKU",
    "estimated_print_time_minutes": "Printtijd min",
    "estimated_filament_grams": "Filament g",
    "default_sale_price": "Verkoopprijs",
    "cost_price": "Kostprijs",
    "quantity_needed": "Nodig",
    "quantity_planned": "Gepland",
    "quantity_succeeded": "Gelukt",
    "quantity_failed": "Mislukt",
    "quantity_to_order": "Naar order",
    "quantity_to_inventory": "Naar voorraad",
    "quantity_sold": "Verkocht",
    "average_weekly_sales": "Gemiddeld per week",
    "revenue": "Omzet",
    "estimated_profit": "Geschatte winst",
    "current_free_stock": "Vrije voorraad",
    "expected_sales": "Verwachte verkoop",
    "safety_stock": "Veiligheidsvoorraad",
    "recommended_stock_level": "Aanbevolen voorraad",
    "recommended_print_quantity": "Printadvies",
    "reason": "Reden",
    "batch_name": "Batchnaam",
    "planned_date": "Geplande datum",
    "estimated_total_print_time_minutes": "Totale printtijd min",
    "estimated_total_filament_grams": "Totaal filament g",
    "print_job_id": "Printtaak",
    "print_batch_id": "Batch",
    "quantity_in_batch": "Aantal in batch",
    "file_path": "Bestand",
    "media_type": "Mediatype",
    "alt_text": "Alt-tekst",
    "sort_order": "Volgorde",
    "is_primary": "Hoofdfoto",
    "key_name": "Sleutelnaam",
    "active": "Actief",
}

VALUE_LABELS = {
    "synchronisatie_nodig": "Synchronisatie nodig",
    "niet_gepubliceerd": "Niet gepubliceerd",
    "klaar_voor_publicatie": "Klaar voor publicatie",
    "gepubliceerd": "Gepubliceerd",
    "gepauzeerd": "Gepauzeerd",
    "gearchiveerd": "Gearchiveerd",
    "volledig_op_voorraad": "Volledig op voorraad",
    "deels_op_voorraad": "Deels op voorraad",
    "niet_op_voorraad": "Niet op voorraad",
    "deels_te_printen": "Deels te printen",
    "volledig_te_printen": "Volledig te printen",
    "volledig_uit_voorraad": "Volledig uit voorraad",
    "nieuw": "Nieuw",
    "gepland": "Gepland",
    "bezig": "Bezig",
    "geprint": "Geprint",
    "deels_mislukt": "Deels mislukt",
    "mislukt": "Mislukt",
    "verwerkt": "Verwerkt",
    "geannuleerd": "Geannuleerd",
    "gereserveerd_voor_order": "Gereserveerd voor order",
    "reservering_vrijgegeven": "Reservering vrijgegeven",
    "print_gereed": "Print gereed",
    "correctie": "Correctie",
    "retour": "Retour",
    "afgekeurd": "Afgekeurd",
}


def friendly_value(value: Any) -> Any:
    if isinstance(value, str):
        return VALUE_LABELS.get(value, value.replace("_", " "))
    return value


@st.cache_data(ttl=30)
def reference_labels(api_base_url: str) -> dict[str, dict[int, str]]:
    def fetch(path: str) -> list[dict[str, Any]]:
        response = requests.get(f"{api_base_url}{path}", timeout=10)
        response.raise_for_status()
        return response.json()

    try:
        products = fetch("/products")
        variants = fetch("/product-variants")
        platforms = fetch("/platforms")
    except Exception:
        return {"products": {}, "variants": {}, "platforms": {}}

    product_labels = {int(product["id"]): product.get("name") or f"Product {product['id']}" for product in products}
    platform_labels = {int(platform["id"]): platform.get("name") or f"Platform {platform['id']}" for platform in platforms}
    variant_labels = {
        int(variant["id"]): " - ".join(
            part
            for part in [variant.get("sku"), variant.get("variant_name")]
            if part
        )
        or f"Variant {variant['id']}"
        for variant in variants
    }
    return {"products": product_labels, "variants": variant_labels, "platforms": platform_labels}


def lookup_label(labels: dict[int, str], value: Any) -> Any:
    try:
        return labels.get(int(value), value)
    except (TypeError, ValueError):
        return value


def enrich_reference_labels(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = reference_labels(API_BASE_URL)
    enriched = []
    for record in records:
        row = dict(record)
        for key in ["product_id", "product"]:
            if key in row:
                row[key] = lookup_label(labels["products"], row[key])
        for key in ["product_variant_id", "variant"]:
            if key in row:
                row[key] = lookup_label(labels["variants"], row[key])
        for key in ["platform_id", "platform"]:
            if key in row:
                row[key] = lookup_label(labels["platforms"], row[key])
        enriched.append(row)
    return enriched


def friendly_dataframe(data: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not data:
        st.info("Geen gegevens gevonden.")
        return

    frame = pd.DataFrame(enrich_reference_labels(data))
    if columns:
        visible_columns = [column for column in columns if column in frame.columns]
        frame = frame[visible_columns]
    frame = frame.map(friendly_value)
    frame = frame.rename(columns={column: COLUMN_LABELS.get(column, column.replace("_", " ").title()) for column in frame.columns})
    st.dataframe(frame, use_container_width=True, hide_index=True)


def show_table(title: str, path: str) -> None:
    st.subheader(title)
    try:
        data = normalized_records(api_get(path))
    except Exception as exc:
        st.error(f"API-fout: {exc}")
        return

    friendly_dataframe(data)


def open_ui_guide() -> None:
    st.session_state.selected_group = "Overzicht"
    st.session_state.selected_page_name = "Handleiding"


def dashboard() -> None:
    page_header(
        "3D Print Manager",
        "Werk vanuit orders, voorraad en printplanning zonder Bambu Studio te vervangen.",
        "NAS actief",
    )
    guide_col, hint_col = st.columns([1, 3])
    guide_col.button("Handleiding openen", use_container_width=True, on_click=open_ui_guide)
    hint_col.caption("Nieuw in de UI: open hier de handleiding als de paginakiezer bovenaan op je telefoon verborgen zit.")

    try:
        products = api_get("/products")
        orders_data = api_get("/orders")
        filament_data = api_get("/filament")
        print_jobs = api_get("/print-jobs")
        inventory = api_get("/inventory/products")
        recommendations = api_get("/stock-recommendations")
        publications = []
        for product in products[:20]:
            publications.extend(api_get(f"/products/{product['id']}/publications"))
    except Exception as exc:
        st.error(f"API-fout: {exc}")
        return

    open_orders = [order for order in orders_data if order.get("status") not in {"verzonden", "geannuleerd"}]
    to_print_orders = [
        order
        for order in orders_data
        if order.get("status") in {"deels_te_printen", "volledig_te_printen", "ingepland"}
    ]
    low_product_stock = [
        item
        for item in inventory
        if int(item.get("minimum_stock_level") or 0) > 0
        and int(item.get("quantity_on_hand") or 0) - int(item.get("quantity_reserved") or 0)
        <= int(item.get("minimum_stock_level") or 0)
    ]
    low_filament = [
        item
        for item in filament_data
        if float(item.get("remaining_weight_grams") or 0) <= float(item.get("minimum_remaining_grams") or 0)
    ]
    sync_needed = [item for item in publications if item.get("publication_status") == "synchronisatie_nodig"]
    open_recommendations = [item for item in recommendations if item.get("status") in {"nieuw", "aangepast"}]
    today_minutes = sum(
        int(job.get("estimated_print_time_minutes") or 0)
        for job in print_jobs
        if job.get("status") in {"nieuw", "gepland", "bezig"}
    )

    st.subheader("Vandaag in het kort")
    st.caption("De belangrijkste aantallen voor orders, printwerk, voorraad en acties.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Open orders", len(open_orders), f"{len(to_print_orders)} met printwerk")
    with col2:
        metric_card("Open printtijd", f"{round(today_minutes / 60, 1)} u", f"{len(print_jobs)} printtaken")
    with col3:
        metric_card("Lage voorraad", len(low_product_stock), f"{len(low_filament)} filamentrollen laag")
    with col4:
        metric_card("Acties", len(open_recommendations) + len(sync_needed), "adviezen en syncs")

    st.subheader("Procesoverzicht")
    st.caption("De normale route van productbeheer naar printvoorbereiding.")
    st.markdown(
        """
        <div class="pm-workflow">
            <div class="pm-step"><strong>Catalogus</strong><span>Product, foto en variant</span></div>
            <div class="pm-step"><strong>Publicatie</strong><span>Etsy en Shopify velden</span></div>
            <div class="pm-step"><strong>Orders</strong><span>Import en SKU-koppeling</span></div>
            <div class="pm-step"><strong>Voorraad</strong><span>Vrij, gereserveerd, tekort</span></div>
            <div class="pm-step"><strong>Planning</strong><span>Batch per kleur en materiaal</span></div>
            <div class="pm-step"><strong>Bambu export</strong><span>Productielijst maken</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Snelle acties")
    st.caption("Gebruik deze knoppen om testdata te laden, orders te importeren of advies te genereren.")
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    if action_col1.button("Dummydata laden", use_container_width=True):
        result = api_post("/seed")
        st.success(result["status"])
        st.rerun()
    if action_col2.button("Voorraadadvies genereren", use_container_width=True):
        result = api_post("/stock-recommendations/generate", {"period_days": 30, "weeks_ahead": 1, "safety_stock": 2})
        st.success(f"{result['generated_count']} nieuw, {result['updated_count']} bijgewerkt.")
        st.rerun()
    if action_col3.button("Etsy dummy-import", use_container_width=True):
        result = api_post("/orders/import/etsy")
        st.success(f"Order {result['order']['internal_order_number']} geimporteerd.")
        st.rerun()
    if action_col4.button("Shopify dummy-import", use_container_width=True):
        result = api_post("/orders/import/shopify")
        st.success(f"Order {result['order']['internal_order_number']} geimporteerd.")
        st.rerun()

    col_a, col_b = st.columns(2)
    with col_a:
        section_start(
            "Orderverwerking",
            "Open orders die nog gecontroleerd, gereserveerd, geprint of verzonden moeten worden.",
        )
        if open_orders:
            rows = [
                {
                    "order": order.get("internal_order_number"),
                    "platform": order.get("platform_id"),
                    "klant": order.get("customer_name"),
                    "datum": order.get("order_date"),
                    "status": order.get("status"),
                    "totaal": order.get("total_amount"),
                }
                for order in open_orders[:8]
            ]
            friendly_dataframe(rows, ["order", "platform", "klant", "datum", "status", "totaal"])
        else:
            st.success("Geen open orders.")
        section_end()
    with col_b:
        section_start(
            "Voorraadadvies",
            "Adviezen om extra voorraad te printen op basis van verkooptrend, vrije voorraad en veiligheidsvoorraad.",
        )
        if open_recommendations:
            rows = [
                {
                    "product": item.get("product"),
                    "variant": item.get("variant"),
                    "vrij": item.get("current_free_stock"),
                    "verwacht": item.get("expected_sales"),
                    "printadvies": item.get("recommended_print_quantity"),
                    "status": item.get("status"),
                }
                for item in open_recommendations[:8]
            ]
            friendly_dataframe(rows, ["product", "variant", "vrij", "verwacht", "printadvies", "status"])
        else:
            st.success("Geen open voorraadadviezen.")
        section_end()

    col_c, col_d = st.columns(2)
    with col_c:
        section_start(
            "Productvoorraad",
            "Productvarianten waarvan de vrije voorraad op of onder het ingestelde minimum zit.",
        )
        rows = [
            {
                "variant": item.get("product_variant_id"),
                "kleur": item.get("color"),
                "materiaal": item.get("material"),
                "vrij": int(item.get("quantity_on_hand") or 0) - int(item.get("quantity_reserved") or 0),
                "minimum": item.get("minimum_stock_level"),
                "locatie": item.get("location"),
            }
            for item in low_product_stock[:8]
        ]
        friendly_dataframe(rows, ["variant", "kleur", "materiaal", "vrij", "minimum", "locatie"])
        section_end()
    with col_d:
        section_start(
            "Publicatiesynchronisatie",
            "Productpublicaties die opnieuw naar Etsy, Shopify of een ander platform gesynchroniseerd moeten worden.",
        )
        if sync_needed:
            rows = [
                {
                    "product": item.get("product_id"),
                    "platform": item.get("platform_id"),
                    "status": item.get("publication_status"),
                    "laatste sync": item.get("last_synced_at"),
                }
                for item in sync_needed[:8]
            ]
            friendly_dataframe(rows, ["product", "platform", "status", "laatste sync"])
        else:
            st.success("Geen publicaties met synchronisatie nodig.")
        section_end()


def ai_product_assistant() -> None:
    page_header(
        "AI Product Assistent",
        "Maak gratis productconcepten in mockmodus. Er worden geen betaalde OpenAI/API-calls gedaan.",
        "mockmodus",
    )
    screen_purpose(
        [
            ("1. Idee invoeren", "Geef kort op wat je wilt verkopen en voor wie het bedoeld is."),
            ("2. Concept controleren", "Bekijk titel, teksten, tags, varianten en platformvelden voordat je iets opslaat."),
            ("3. Zelf goedkeuren", "Pas na jouw akkoord wordt het concept als intern product aangemaakt."),
        ]
    )
    work_hint(
        "Mockmodus kost niets. Echte AI met gpt-5.4-mini gebruikt OpenAI API-tegoed en werkt alleen als jij dit expliciet aanzet."
    )
    try:
        ai_status = api_get("/ai/product-draft/status")
    except Exception as exc:
        ai_status = {"ready": False, "enabled": False, "configured": False, "model": "gpt-5.4-mini", "note": str(exc)}

    col_status_1, col_status_2, col_status_3 = st.columns(3)
    col_status_1.metric("AI-modus", "aan" if ai_status.get("enabled") else "uit")
    col_status_2.metric("API-key", "ingesteld" if ai_status.get("configured") else "ontbreekt")
    col_status_3.metric("Model", ai_status.get("model") or "gpt-5.4-mini")
    if ai_status.get("ready"):
        st.warning("Echte AI staat klaar. Gebruik de gpt-5.4-mini knop alleen bewust; dit kan API-kosten maken.")
    else:
        st.info("Echte AI staat nog uit. Je kunt gratis blijven testen met mockmodus.")

    st.session_state.setdefault("ai_product_draft", None)

    section_start(
        "1. Productidee invoeren",
        "Vul alleen de basis in. De assistent maakt hieruit een concept voor producttekst, SEO, varianten en platformvelden.",
    )
    with st.form("ai_product_assistant_form"):
        col1, col2 = st.columns(2)
        idea = col1.text_input("Wat wil je maken?", placeholder="Bijvoorbeeld: plantenpot met geometrisch patroon")
        audience = col2.text_input("Doelgroep", placeholder="Bijvoorbeeld: plantenliefhebbers, interieurfans")
        col3, col4, col5 = st.columns(3)
        style = col3.text_input("Stijl", placeholder="Bijvoorbeeld: minimalistisch, speels, luxe")
        material = col4.text_input("Materiaal", value="PLA")
        colors = col5.text_input("Kleuren", placeholder="Bijvoorbeeld: zwart, wit, terracotta")
        col6, col7, col8 = st.columns(3)
        product_type = col6.text_input("Producttype", value="3D print product")
        category = col7.text_input("Categorie", placeholder="Bijvoorbeeld: woondecoratie")
        price = col8.number_input("Richtprijs", min_value=0.0, value=0.0, step=0.50)
        col9, col10, col11 = st.columns(3)
        print_time = col9.number_input("Printtijd per stuk minuten", min_value=0, value=0, step=5)
        filament = col10.number_input("Filament per stuk gram", min_value=0.0, value=0.0, step=1.0)
        dimensions = col11.text_input("Afmetingen", placeholder="Bijvoorbeeld: 120 x 90 x 90 mm")
        keywords = st.text_input(
            "Extra zoekwoorden optioneel",
            placeholder="Laat leeg als de assistent zelf tags moet afleiden",
        )
        st.caption("De assistent bedenkt zelf tags uit je invoer. Extra zoekwoorden hierboven worden letterlijk toegevoegd als je ze invult.")
        platforms = st.multiselect("Platformteksten voorbereiden voor", ["Etsy", "Shopify"], default=["Etsy", "Shopify"])
        mock_submitted = st.form_submit_button("Concept genereren (gratis mock)")
        ai_submitted = st.form_submit_button(
            f"Concept genereren met {ai_status.get('model') or 'gpt-5.4-mini'}",
            disabled=not ai_status.get("ready"),
        )

    payload = {
        "idea": idea,
        "audience": audience,
        "style": style,
        "material": material,
        "colors": colors,
        "product_type": product_type,
        "category": category,
        "price": price,
        "print_time": print_time,
        "filament": filament,
        "dimensions": dimensions,
        "keywords": keywords,
        "platforms": platforms,
    }

    if mock_submitted and not idea.strip():
        st.error("Vul eerst in wat je wilt maken.")
    elif mock_submitted:
        st.session_state.ai_product_draft = generate_mock_product_draft(
            **payload,
        )
        st.success("Concept gegenereerd. Bekijk hieronder de preview voordat je opslaat.")
    elif ai_submitted and not idea.strip():
        st.error("Vul eerst in wat je wilt maken.")
    elif ai_submitted:
        try:
            st.session_state.ai_product_draft = api_post("/ai/product-draft/generate", payload)
            st.success(f"Concept gegenereerd met {ai_status.get('model')}. Controleer de output voordat je opslaat.")
        except requests.HTTPError as exc:
            st.error(f"Echte AI-generatie mislukt: {exc.response.text}")
        except Exception as exc:
            st.error(f"Echte AI-generatie mislukt: {exc}")
    section_end()

    draft = st.session_state.get("ai_product_draft")
    preview_tab, json_tab, save_tab = st.tabs(["2. Concept controleren", "JSON", "3. Opslaan"])

    with preview_tab:
        if not draft:
            st.info("Vul hierboven eerst je productidee in en klik op Concept genereren.")
        else:
            render_ai_product_preview(draft)

    with json_tab:
        if not draft:
            st.info("Nog geen concept beschikbaar.")
        else:
            st.caption("Deze structuur is bewust vergelijkbaar met wat een echte OpenAI Structured Output later kan teruggeven.")
            st.json(draft)

    with save_tab:
        if not draft:
            st.info("Genereer eerst een concept voordat je kunt opslaan.")
        else:
            st.subheader("Concept omzetten naar product")
            st.warning(
                "Opslaan maakt echte records aan in de productcatalogus. Er wordt niets gepubliceerd naar verkoopplatformen."
            )
            confirm = st.checkbox("Ik heb het concept gecontroleerd en wil dit opslaan.", key="ai_save_confirm")
            save_publications = st.checkbox(
                "Maak ook platformpublicatie-concepten aan voor bestaande Etsy/Shopify platformen.",
                value=True,
                key="ai_save_publications",
            )
            if st.button("Concept opslaan in productcatalogus", disabled=not confirm):
                try:
                    result = save_ai_product_draft(draft, save_publications=save_publications)
                    st.success(f"Product opgeslagen: {result['product_name']}")
                    if result["warnings"]:
                        for warning in result["warnings"]:
                            st.warning(warning)
                    st.session_state.ai_product_draft = None
                except requests.HTTPError as exc:
                    st.error(f"Opslaan mislukt: {exc.response.text}")
                except Exception as exc:
                    st.error(f"Opslaan mislukt: {exc}")


def generate_mock_product_draft(
    *,
    idea: str,
    audience: str,
    style: str,
    material: str,
    colors: str,
    product_type: str,
    category: str,
    price: float,
    print_time: int,
    filament: float,
    dimensions: str,
    keywords: str,
    platforms: list[str],
) -> dict[str, Any]:
    clean_idea = idea.strip() or "Nieuw 3D print product"
    clean_material = material.strip() or "PLA"
    color_list = split_words(colors) or ["naturel"]
    base_slug = slugify(clean_idea)
    title = f"{clean_idea} - 3D geprint {category.lower() if category else 'product'}"
    short_description = f"3D geprint {clean_idea.lower()} in {clean_material}, ontworpen voor {audience.strip() or 'dagelijks gebruik'}."
    long_description = (
        f"Deze {clean_idea.lower()} wordt laag voor laag 3D geprint in {clean_material}. "
        f"De uitstraling is {style.strip() or 'netjes en modern'}, waardoor het product geschikt is voor "
        f"{audience.strip() or 'de doelgroep die je later specificeert'}. "
        f"Afmetingen: {dimensions.strip() or 'nog te bepalen'}."
    )
    sales_description = (
        f"Geef je collectie een persoonlijk accent met deze {clean_idea.lower()}. "
        "Licht, betaalbaar en geschikt om in meerdere kleuren te produceren."
    )
    seo_title = title[:70]
    seo_description = short_description[:155]
    tags = suggest_product_tags(
        idea=clean_idea,
        audience=audience,
        style=style,
        material=clean_material,
        colors=color_list,
        product_type=product_type,
        category=category,
        extra_keywords=keywords,
    )
    variants = []
    for index, color in enumerate(color_list, start=1):
        color_slug = slugify(color).upper().replace("-", "")
        variants.append(
            {
                "variant_name": f"{color} {clean_material}",
                "sku": f"{base_slug.upper().replace('-', '')[:14]}-{color_slug[:6]}-{index:02d}",
                "color": color,
                "material": clean_material,
                "size": dimensions.strip() or None,
                "finish": "standaard",
                "estimated_print_time_minutes": print_time or None,
                "estimated_filament_grams": filament or None,
                "default_sale_price": round(float(price or 0), 2) or None,
                "active": True,
            }
        )

    publication_map = {}
    for platform in platforms:
        key = platform.lower()
        if key == "etsy":
            publication_map[key] = {
                "platform_title": f"{clean_idea} | 3D geprint | {clean_material}",
                "platform_description": f"{sales_description}\n\nMateriaal: {clean_material}\nKleuren: {', '.join(color_list)}",
                "platform_category": category or "Handmade gifts",
                "platform_tags": ", ".join(tags[:10]),
                "platform_price_override": round(float(price or 0), 2) or None,
                "publication_status": "concept",
            }
        if key == "shopify":
            publication_map[key] = {
                "platform_title": title,
                "platform_description": long_description,
                "platform_category": category or product_type or "3D prints",
                "platform_tags": ", ".join(tags),
                "platform_price_override": round(float(price or 0), 2) or None,
                "publication_status": "concept",
            }

    warnings = [
        "Controleer afmetingen, printtijd en filamentverbruik met een echte testprint.",
        "Voeg productfoto's toe voordat je publiceert.",
        "Controleer platformregels voordat je live publiceert.",
    ]

    return {
        "product": {
            "name": clean_idea,
            "internal_title": title,
            "short_description": short_description,
            "long_description": long_description,
            "sales_description": sales_description,
            "seo_title": seo_title,
            "seo_description": seo_description,
            "product_type": product_type.strip() or "3D print product",
            "internal_category": category.strip() or "Ongecategoriseerd",
            "status": "concept",
            "active": True,
        },
        "tags": tags,
        "variants": variants,
        "platform_publications": publication_map,
        "checklist": warnings,
        "source": "mockmodus_zonder_betaalde_ai_call",
    }


def render_ai_product_preview(draft: dict[str, Any]) -> None:
    product = draft["product"]
    record_card(
        product.get("internal_title") or product.get("name"),
        product.get("short_description") or "",
        product.get("status"),
        [
            ("Categorie", product.get("internal_category")),
            ("Producttype", product.get("product_type")),
            ("SEO titel", product.get("seo_title")),
        ],
    )
    col1, col2 = st.columns(2)
    with col1:
        section_start("Productteksten", "Deze teksten komen in de centrale productcatalogus.")
        st.markdown(f"**Korte omschrijving**\n\n{product.get('short_description')}")
        st.markdown(f"**Lange omschrijving**\n\n{product.get('long_description')}")
        st.markdown(f"**Verkooptekst**\n\n{product.get('sales_description')}")
        section_end()
    with col2:
        section_start("Controlepunten", "Deze punten moet je zelf nalopen voordat je publiceert.")
        for item in draft.get("checklist", []):
            st.write(f"- {item}")
        section_end()

    section_start("Varianten", "Per kleur wordt alvast een variant met SKU, materiaal, printtijd en prijs gemaakt.")
    friendly_dataframe(draft.get("variants", []))
    section_end()

    section_start("Tags", "Zoekwoorden voor interne vindbaarheid en platformpublicatie.")
    st.write(", ".join(draft.get("tags", [])) or "Geen tags")
    section_end()

    publications = [
        {"platform": platform, **payload}
        for platform, payload in draft.get("platform_publications", {}).items()
    ]
    if publications:
        section_start("Platformconcepten", "Deze worden alleen als concept opgeslagen, niet gepubliceerd.")
        friendly_dataframe(publications)
        section_end()


def save_ai_product_draft(draft: dict[str, Any], save_publications: bool) -> dict[str, Any]:
    product = api_post("/products", clean_payload(draft["product"]))
    product_id = product["id"]
    for tag in draft.get("tags", []):
        api_post(f"/products/{product_id}/tags", {"tag": tag})
    for variant in draft.get("variants", []):
        api_post("/product-variants", clean_payload({**variant, "product_id": product_id}))

    warnings = []
    if save_publications:
        platforms = api_get("/platforms")
        platforms_by_type = {str(platform.get("type", "")).lower(): platform for platform in platforms}
        for platform_type, publication in draft.get("platform_publications", {}).items():
            platform = platforms_by_type.get(platform_type)
            if not platform:
                warnings.append(f"Geen actief platform gevonden voor {platform_type}; publicatieconcept niet aangemaakt.")
                continue
            api_post(
                f"/products/{product_id}/publications",
                clean_payload({"platform_id": platform["id"], **publication}),
            )

    return {"product_id": product_id, "product_name": product.get("name"), "warnings": warnings}


def product_catalog() -> None:
    page_header(
        "Productcatalogus",
        "Beheer interne producten als hoofdbron voor voorraad, publicaties en printplanning.",
    )
    screen_purpose(
        [
            ("1. Product aanmaken", "Maak eerst het interne product met titel, omschrijving, categorie en status."),
            ("2. Varianten toevoegen", "Maak daarna uitvoeringen zoals kleur of materiaal met SKU, printtijd en filamentverbruik."),
            ("3. Klaarzetten", "Als de basis klopt, ga je verder met foto's, voorraad en platformpublicatie."),
        ]
    )
    workflow_steps(
        "Werkvolgorde productbeheer",
        [
            ("Product", "Naam en teksten"),
            ("Variant", "SKU en printinfo"),
            ("Foto", "Upload en hoofdfoto"),
            ("Publicatie", "Platformvelden"),
            ("Voorraad", "Minimum en locatie"),
            ("Sync", "Later publiceren"),
        ],
    )
    tab_products, tab_variants = st.tabs(["Producten", "Varianten"])

    with tab_products:
        products = api_get("/products")
        variants = api_get("/product-variants")
        product_ids_with_variants = {variant.get("product_id") for variant in variants}
        ready_products = [product for product in products if product.get("status") == "klaar_voor_publicatie"]
        published_products = [product for product in products if product.get("status") == "gepubliceerd"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("Producten", len(products), "interne catalogus")
        with col2:
            metric_card("Varianten", len(variants), "SKU's en printinfo")
        with col3:
            metric_card("Publiceerbaar", len(ready_products), "klaar voor platformcheck")
        with col4:
            metric_card("Gepubliceerd", len(published_products), "actief op platformen")

        work_hint("Start met een product, voeg daarna varianten en foto's toe. Publicatie volgt pas als de basisvelden compleet zijn.")

        with st.expander("Nieuw product", expanded=False):
            with st.form("create_product"):
                col1, col2 = st.columns(2)
                name = col1.text_input("Interne naam")
                internal_title = col2.text_input("Producttitel")
                short_description = st.text_area("Korte omschrijving", height=80)
                long_description = st.text_area("Lange omschrijving", height=120)
                sales_description = st.text_area("Verkooptekst", height=100)
                col_seo1, col_seo2 = st.columns(2)
                seo_title = col_seo1.text_input("SEO-titel")
                seo_description = col_seo2.text_input("SEO-omschrijving")
                col3, col4, col5 = st.columns(3)
                product_type = col3.text_input("Producttype")
                internal_category = col4.text_input("Categorie")
                status = col5.selectbox(
                    "Status",
                    ["concept", "klaar_voor_publicatie", "gepubliceerd", "gepauzeerd", "gearchiveerd"],
                )
                active = st.checkbox("Actief", value=True)
                submitted = st.form_submit_button("Product opslaan")

            if submitted:
                if not name:
                    st.error("Interne naam is verplicht.")
                else:
                    payload = clean_payload(
                        {
                            "name": name,
                            "internal_title": internal_title,
                            "short_description": short_description,
                            "long_description": long_description,
                            "sales_description": sales_description,
                            "seo_title": seo_title,
                            "seo_description": seo_description,
                            "product_type": product_type,
                            "internal_category": internal_category,
                            "status": status,
                            "active": active,
                        }
                    )
                    api_post("/products", payload)
                    st.success("Product opgeslagen.")
                    st.rerun()

        if products:
            visible_products = filter_by_status(products, "product_catalog_status")
            st.subheader("Producten")
            columns = st.columns(2)
            variant_counts = {
                product["id"]: len([variant for variant in variants if variant.get("product_id") == product["id"]])
                for product in products
            }
            for index, product in enumerate(visible_products[:8]):
                with columns[index % 2]:
                    record_card(
                        product.get("internal_title") or product.get("name"),
                        product.get("internal_category") or product.get("product_type") or "Geen categorie",
                        product.get("status"),
                        [
                            ("Interne naam", product.get("name")),
                            ("Varianten", variant_counts.get(product["id"], 0)),
                            ("Publicatiebasis", "variant aanwezig" if product["id"] in product_ids_with_variants else "variant ontbreekt"),
                        ],
                    )
            if len(visible_products) > 8:
                st.caption(f"{len(visible_products) - 8} extra producten staan in de tabel hieronder.")
            friendly_dataframe(
                [
                    {
                        "id": product.get("id"),
                        "naam": product.get("name"),
                        "titel": product.get("internal_title"),
                        "categorie": product.get("internal_category"),
                        "type": product.get("product_type"),
                        "status": product.get("status"),
                        "varianten": variant_counts.get(product["id"], 0),
                        "actief": product.get("active"),
                    }
                    for product in visible_products
                ],
                ["id", "naam", "titel", "categorie", "type", "status", "varianten", "actief"],
            )
        else:
            st.info("Nog geen producten. Maak je eerste interne product aan of laad dummydata via het dashboard.")

    with tab_variants:
        products = api_get("/products")
        if not products:
            st.info("Maak eerst een product aan.")
        else:
            with st.expander("Nieuwe productvariant", expanded=False):
                with st.form("create_variant"):
                    product_id = st.selectbox(
                        "Product",
                        [product["id"] for product in products],
                        format_func=lambda x: product_name(products, x),
                    )
                    col1, col2, col3 = st.columns(3)
                    variant_name = col1.text_input("Variantnaam")
                    sku = col2.text_input("SKU")
                    default_sale_price = col3.number_input("Verkoopprijs", min_value=0.0, step=0.50)
                    col4, col5, col6 = st.columns(3)
                    color = col4.text_input("Kleur")
                    material = col5.text_input("Materiaal")
                    cost_price = col6.number_input("Kostprijs", min_value=0.0, step=0.10)
                    col7, col8, col9 = st.columns(3)
                    estimated_print_time_minutes = col7.number_input("Printtijd minuten", min_value=0, step=5)
                    estimated_filament_grams = col8.number_input("Filament gram", min_value=0.0, step=1.0)
                    print_file_path = col9.text_input("3MF/STL pad")
                    col10, col11, col12 = st.columns(3)
                    size = col10.text_input("Maat")
                    finish = col11.text_input("Afwerking")
                    action_sale_price = col12.number_input("Actieprijs", min_value=0.0, step=0.50)
                    col13, col14, col15, col16 = st.columns(4)
                    weight_grams = col13.number_input("Gewicht gram", min_value=0.0, step=1.0)
                    length_mm = col14.number_input("Lengte mm", min_value=0.0, step=1.0)
                    width_mm = col15.number_input("Breedte mm", min_value=0.0, step=1.0)
                    height_mm = col16.number_input("Hoogte mm", min_value=0.0, step=1.0)
                    submitted = st.form_submit_button("Variant opslaan")

                if submitted:
                    if not variant_name or not sku:
                        st.error("Variantnaam en SKU zijn verplicht.")
                    else:
                        payload = clean_payload(
                            {
                                "product_id": product_id,
                                "variant_name": variant_name,
                                "sku": sku,
                                "color": color,
                                "material": material,
                                "size": size,
                                "finish": finish,
                                "print_file_path": print_file_path,
                                "estimated_print_time_minutes": estimated_print_time_minutes or None,
                                "estimated_filament_grams": estimated_filament_grams or None,
                                "weight_grams": weight_grams or None,
                                "length_mm": length_mm or None,
                                "width_mm": width_mm or None,
                                "height_mm": height_mm or None,
                                "default_sale_price": default_sale_price or None,
                                "action_sale_price": action_sale_price or None,
                                "cost_price": cost_price or None,
                                "active": True,
                            }
                        )
                        api_post("/product-variants", payload)
                        st.success("Variant opgeslagen.")
                        st.rerun()

            variants = api_get("/product-variants")
            if variants:
                with st.expander("Productvariant bewerken", expanded=False):
                    variant_id = st.selectbox(
                        "Variant",
                        [variant["id"] for variant in variants],
                        format_func=lambda x: next(
                            f"{v['sku']} - {v['variant_name']}" for v in variants if v["id"] == x
                        ),
                    )
                    variant = next(v for v in variants if v["id"] == variant_id)
                    with st.form("edit_variant"):
                        product_id = st.selectbox(
                            "Product",
                            [product["id"] for product in products],
                            index=[product["id"] for product in products].index(variant["product_id"]),
                            format_func=lambda x: product_name(products, x),
                        )
                        col1, col2, col3 = st.columns(3)
                        variant_name = col1.text_input("Variantnaam", value=variant.get("variant_name") or "")
                        sku = col2.text_input("SKU", value=variant.get("sku") or "")
                        default_sale_price = col3.number_input(
                            "Verkoopprijs",
                            min_value=0.0,
                            value=float(variant.get("default_sale_price") or 0),
                            step=0.50,
                        )
                        col4, col5, col6 = st.columns(3)
                        color = col4.text_input("Kleur", value=variant.get("color") or "")
                        material = col5.text_input("Materiaal", value=variant.get("material") or "")
                        cost_price = col6.number_input(
                            "Kostprijs",
                            min_value=0.0,
                            value=float(variant.get("cost_price") or 0),
                            step=0.10,
                        )
                        col7, col8, col9 = st.columns(3)
                        estimated_print_time_minutes = col7.number_input(
                            "Printtijd minuten",
                            min_value=0,
                            value=int(variant.get("estimated_print_time_minutes") or 0),
                            step=5,
                        )
                        estimated_filament_grams = col8.number_input(
                            "Filament gram",
                            min_value=0.0,
                            value=float(variant.get("estimated_filament_grams") or 0),
                            step=1.0,
                        )
                        print_file_path = col9.text_input("3MF/STL pad", value=variant.get("print_file_path") or "")
                        col10, col11, col12 = st.columns(3)
                        size = col10.text_input("Maat", value=variant.get("size") or "")
                        finish = col11.text_input("Afwerking", value=variant.get("finish") or "")
                        action_sale_price = col12.number_input(
                            "Actieprijs",
                            min_value=0.0,
                            value=float(variant.get("action_sale_price") or 0),
                            step=0.50,
                        )
                        col13, col14, col15, col16 = st.columns(4)
                        weight_grams = col13.number_input(
                            "Gewicht gram", min_value=0.0, value=float(variant.get("weight_grams") or 0), step=1.0
                        )
                        length_mm = col14.number_input(
                            "Lengte mm", min_value=0.0, value=float(variant.get("length_mm") or 0), step=1.0
                        )
                        width_mm = col15.number_input(
                            "Breedte mm", min_value=0.0, value=float(variant.get("width_mm") or 0), step=1.0
                        )
                        height_mm = col16.number_input(
                            "Hoogte mm", min_value=0.0, value=float(variant.get("height_mm") or 0), step=1.0
                        )
                        active = st.checkbox("Actief", value=bool(variant.get("active", True)), key="edit_variant_active")
                        submitted = st.form_submit_button("Variant wijzigen")

                    if submitted:
                        if not variant_name or not sku:
                            st.error("Variantnaam en SKU zijn verplicht.")
                        else:
                            payload = clean_payload(
                                {
                                    "product_id": product_id,
                                    "variant_name": variant_name,
                                    "sku": sku,
                                    "color": color,
                                    "material": material,
                                    "size": size,
                                    "finish": finish,
                                    "print_file_path": print_file_path,
                                    "estimated_print_time_minutes": estimated_print_time_minutes or None,
                                    "estimated_filament_grams": estimated_filament_grams or None,
                                    "weight_grams": weight_grams or None,
                                    "length_mm": length_mm or None,
                                    "width_mm": width_mm or None,
                                    "height_mm": height_mm or None,
                                    "default_sale_price": default_sale_price or None,
                                    "action_sale_price": action_sale_price or None,
                                    "cost_price": cost_price or None,
                                    "active": active,
                                }
                            )
                            api_put(f"/product-variants/{variant_id}", payload)
                            st.success("Variant bijgewerkt.")
                            st.rerun()

        show_table("Productvarianten", "/product-variants")


def product_detail() -> None:
    st.title("Productdetail")
    products = api_get("/products")
    if not products:
        st.info("Laad eerst dummydata of maak producten aan via de API.")
        return
    product_id = st.selectbox(
        "Product",
        [product["id"] for product in products],
        format_func=lambda x: product_name(products, x),
    )
    product = api_get(f"/products/{product_id}")
    tab_base, tab_variants, tab_media, tab_tags = st.tabs(["Basis", "Varianten", "Foto's", "Tags"])

    with tab_base:
        with st.form("edit_product"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Interne naam", value=product.get("name") or "")
            internal_title = col2.text_input("Producttitel", value=product.get("internal_title") or "")
            short_description = st.text_area("Korte omschrijving", value=product.get("short_description") or "", height=80)
            long_description = st.text_area("Lange omschrijving", value=product.get("long_description") or "", height=120)
            sales_description = st.text_area("Verkooptekst", value=product.get("sales_description") or "", height=100)
            col3, col4 = st.columns(2)
            seo_title = col3.text_input("SEO-titel", value=product.get("seo_title") or "")
            seo_description = col4.text_area("SEO-omschrijving", value=product.get("seo_description") or "", height=80)
            col5, col6, col7 = st.columns(3)
            product_type = col5.text_input("Producttype", value=product.get("product_type") or "")
            internal_category = col6.text_input("Categorie", value=product.get("internal_category") or "")
            status_options = ["concept", "klaar_voor_publicatie", "gepubliceerd", "gepauzeerd", "gearchiveerd"]
            current_status = product.get("status") if product.get("status") in status_options else "concept"
            status = col7.selectbox("Status", status_options, index=status_options.index(current_status))
            active = st.checkbox("Actief", value=bool(product.get("active", True)))
            submitted = st.form_submit_button("Wijzigingen opslaan")

        if submitted:
            if not name:
                st.error("Interne naam is verplicht.")
            else:
                api_put(
                    f"/products/{product_id}",
                    clean_payload(
                        {
                            "name": name,
                            "internal_title": internal_title,
                            "short_description": short_description,
                            "long_description": long_description,
                            "sales_description": sales_description,
                            "seo_title": seo_title,
                            "seo_description": seo_description,
                            "product_type": product_type,
                            "internal_category": internal_category,
                            "status": status,
                            "active": active,
                        }
                    ),
                )
                st.success("Product bijgewerkt.")
                st.rerun()

    with tab_variants:
        variants = [variant for variant in api_get("/product-variants") if variant["product_id"] == product_id]
        if variants:
            friendly_dataframe(variants)
        else:
            st.info("Geen varianten gevonden.")

    with tab_media:
        manage_product_media(product_id)

    with tab_tags:
        manage_product_tags(product_id)


def product_media() -> None:
    st.title("Productfoto's")
    products = api_get("/products")
    if not products:
        st.info("Geen producten gevonden.")
        return
    product_id = st.selectbox(
        "Product",
        [product["id"] for product in products],
        format_func=lambda x: product_name(products, x),
    )
    manage_product_media(product_id)


def manage_product_media(product_id: int) -> None:
    with st.form(f"upload_media_{product_id}"):
        uploaded_file = st.file_uploader("Foto uploaden", type=["jpg", "jpeg", "png", "webp", "gif"])
        col1, col2, col3 = st.columns([3, 1, 1])
        upload_alt_text = col1.text_input("Alt-tekst upload")
        upload_sort_order = col2.number_input("Volgorde upload", min_value=0, step=1)
        upload_is_primary = col3.checkbox("Hoofdfoto upload")
        upload_submitted = st.form_submit_button("Foto uploaden")

    if upload_submitted:
        if not uploaded_file:
            st.error("Selecteer eerst een foto.")
        else:
            api_upload(
                f"/products/{product_id}/media/upload",
                uploaded_file,
                {
                    "alt_text": upload_alt_text,
                    "sort_order": str(upload_sort_order),
                    "is_primary": str(upload_is_primary).lower(),
                },
            )
            st.success("Foto geupload.")
            st.rerun()

    with st.expander("Media via pad of URL toevoegen", expanded=False):
        with st.form(f"create_media_{product_id}"):
            col1, col2 = st.columns([3, 1])
            file_path = col1.text_input("Bestandspad of URL")
            media_type = col2.selectbox("Type", ["image", "video", "document"])
            col3, col4, col5 = st.columns([3, 1, 1])
            alt_text = col3.text_input("Alt-tekst")
            sort_order = col4.number_input("Volgorde", min_value=0, step=1)
            is_primary = col5.checkbox("Hoofdfoto")
            submitted = st.form_submit_button("Media toevoegen")

        if submitted:
            if not file_path:
                st.error("Bestandspad of URL is verplicht.")
            else:
                api_post(
                    f"/products/{product_id}/media",
                    clean_payload(
                        {
                            "file_path": file_path,
                            "media_type": media_type,
                            "alt_text": alt_text,
                            "sort_order": sort_order,
                            "is_primary": is_primary,
                        }
                    ),
                )
                st.success("Media toegevoegd.")
                st.rerun()

    media = api_get(f"/products/{product_id}/media")
    if not media:
        st.info("Geen media gevonden.")
        return

    image_media = [item for item in media if item.get("media_type") == "image"]
    if image_media:
        st.subheader("Foto's")
        columns = st.columns(3)
        for index, item in enumerate(image_media):
            with columns[index % 3]:
                image_bytes = uploaded_media_bytes(item.get("file_path"))
                if image_bytes:
                    st.image(image_bytes, caption=item.get("alt_text") or item.get("file_path"), use_container_width=True)
                elif item.get("file_path", "").startswith(("http://", "https://")):
                    st.image(item["file_path"], caption=item.get("alt_text") or item.get("file_path"), use_container_width=True)
                else:
                    st.write(item.get("file_path"))
                if item.get("is_primary"):
                    st.caption("Hoofdfoto")

    friendly_dataframe(media)
    with st.expander("Media bewerken of verwijderen", expanded=False):
        media_id = st.selectbox(
            "Media-item",
            [item["id"] for item in media],
            format_func=lambda x: next(f"{m['sort_order']} - {m['file_path']}" for m in media if m["id"] == x),
        )
        item = next(m for m in media if m["id"] == media_id)
        with st.form(f"edit_media_{media_id}"):
            col1, col2 = st.columns([3, 1])
            file_path = col1.text_input("Bestandspad of URL", value=item.get("file_path") or "")
            media_type = col2.selectbox(
                "Type", ["image", "video", "document"], index=["image", "video", "document"].index(item.get("media_type") or "image")
            )
            col3, col4, col5 = st.columns([3, 1, 1])
            alt_text = col3.text_input("Alt-tekst", value=item.get("alt_text") or "")
            sort_order = col4.number_input("Volgorde", min_value=0, value=int(item.get("sort_order") or 0), step=1)
            is_primary = col5.checkbox("Hoofdfoto", value=bool(item.get("is_primary")))
            save = st.form_submit_button("Media wijzigen")

        col_delete, _ = st.columns([1, 3])
        delete = col_delete.button("Media verwijderen", key=f"delete_media_{media_id}")

        if save:
            api_put(
                f"/product-media/{media_id}",
                clean_payload(
                    {
                        "file_path": file_path,
                        "media_type": media_type,
                        "alt_text": alt_text,
                        "sort_order": sort_order,
                        "is_primary": is_primary,
                    }
                ),
            )
            st.success("Media bijgewerkt.")
            st.rerun()

        if delete:
            api_delete(f"/product-media/{media_id}")
            st.success("Media verwijderd.")
            st.rerun()


def manage_product_tags(product_id: int) -> None:
    with st.form(f"create_tag_{product_id}"):
        tag = st.text_input("Nieuwe tag")
        submitted = st.form_submit_button("Tag toevoegen")

    if submitted:
        if not tag:
            st.error("Tag is verplicht.")
        else:
            api_post(f"/products/{product_id}/tags", {"tag": tag})
            st.success("Tag toegevoegd.")
            st.rerun()

    tags = api_get(f"/products/{product_id}/tags")
    if not tags:
        st.info("Geen tags gevonden.")
        return

    friendly_dataframe(tags)
    tag_id = st.selectbox("Tag verwijderen", [item["id"] for item in tags], format_func=lambda x: next(t["tag"] for t in tags if t["id"] == x))
    if st.button("Geselecteerde tag verwijderen"):
        api_delete(f"/product-tags/{tag_id}")
        st.success("Tag verwijderd.")
        st.rerun()


def platform_publication() -> None:
    page_header(
        "Platformpublicatie",
        "Beheer per platform afwijkende teksten, prijzen, tags, foto's en publicatiestatus.",
    )
    screen_purpose(
        [
            ("Platformvelden", "Vul afwijkende titel, omschrijving, categorie, tags en prijs per platform in."),
            ("Controle", "Laat de app checken of alle verplichte velden en foto's aanwezig zijn."),
            ("Publiceren", "Publiceer of synchroniseer pas nadat de controle geen blokkerende fouten meer toont."),
        ]
    )
    workflow_steps(
        "Werkvolgorde platformpublicatie",
        [
            ("Platform", "Maak Etsy of Shopify aan"),
            ("Velden", "Vul titel, categorie, tags en prijs"),
            ("Foto's", "Kies platformfoto's en volgorde"),
            ("Controle", "Los verplichte velden op"),
            ("Publiceer", "Stuur naar het platform"),
            ("Sync", "Werk wijzigingen later bij"),
        ],
    )
    tabs = st.tabs(["Publicaties", "Platformen"])

    with tabs[0]:
        manage_publications()

    with tabs[1]:
        manage_platforms()


def manage_platforms() -> None:
    with st.expander("Nieuw platform", expanded=False):
        with st.form("create_platform"):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Naam")
            platform_type = col2.selectbox("Type", ["etsy", "shopify", "woocommerce", "ebay", "other"])
            api_base_url = col3.text_input("API basis-URL")
            active = st.checkbox("Actief", value=True, key="create_platform_active")
            submitted = st.form_submit_button("Platform opslaan")

        if submitted:
            if not name:
                st.error("Platformnaam is verplicht.")
            else:
                api_post(
                    "/platforms",
                    clean_payload(
                        {
                            "name": name,
                            "type": platform_type,
                            "api_base_url": api_base_url,
                            "active": active,
                        }
                    ),
                )
                st.success("Platform opgeslagen.")
                st.rerun()

    platforms = api_get("/platforms")
    if platforms:
        with st.expander("Platform bewerken", expanded=False):
            platform_id = st.selectbox(
                "Platform",
                [platform["id"] for platform in platforms],
                format_func=lambda x: next(p["name"] for p in platforms if p["id"] == x),
            )
            platform = next(p for p in platforms if p["id"] == platform_id)
            with st.form("edit_platform"):
                col1, col2, col3 = st.columns(3)
                name = col1.text_input("Naam", value=platform.get("name") or "")
                types = ["etsy", "shopify", "woocommerce", "ebay", "other"]
                current_type = platform.get("type") if platform.get("type") in types else "other"
                platform_type = col2.selectbox("Type", types, index=types.index(current_type))
                api_base_url = col3.text_input("API basis-URL", value=platform.get("api_base_url") or "")
                active = st.checkbox("Actief", value=bool(platform.get("active", True)), key="edit_platform_active")
                submitted = st.form_submit_button("Wijzigingen opslaan")

            if submitted:
                api_put(
                    f"/platforms/{platform_id}",
                    clean_payload(
                        {
                            "name": name,
                            "type": platform_type,
                            "api_base_url": api_base_url,
                            "active": active,
                        }
                    ),
                )
                st.success("Platform bijgewerkt.")
                st.rerun()
            manage_platform_connector(platform_id)

    show_table("Platformen", "/platforms")


def manage_platform_connector(platform_id: int) -> None:
    st.subheader("Connector")
    try:
        status = api_get(f"/platforms/{platform_id}/connector-status")
        credentials = api_get(f"/platforms/{platform_id}/credentials")
    except Exception as exc:
        st.error(f"Connectorstatus kon niet worden opgehaald: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Modus", status.get("mode", "onbekend"))
    col2.metric("Type", status.get("platform_type", "generic"))
    col3.metric("Live compleet", "ja" if status.get("ready_for_live") else "nee")
    if status.get("missing_credentials"):
        st.warning("Ontbrekende credentials: " + ", ".join(status["missing_credentials"]))
    if credentials:
        friendly_dataframe(credentials)
    else:
        st.info("Nog geen credentials opgeslagen voor dit platform.")

    with st.form(f"credential_form_{platform_id}"):
        key_name = st.text_input("Credential key")
        encrypted_value = st.text_input("Credential waarde", type="password")
        submitted = st.form_submit_button("Credential opslaan")
    if submitted:
        api_post(
            f"/platforms/{platform_id}/credentials",
            clean_payload({"key_name": key_name, "encrypted_value": encrypted_value}),
        )
        st.success("Credential opgeslagen.")
        st.rerun()

    if credentials:
        credential_id = st.selectbox(
            "Credential verwijderen",
            [credential["id"] for credential in credentials],
            format_func=lambda x: next(c["key_name"] for c in credentials if c["id"] == x),
        )
        if st.button("Credential verwijderen"):
            api_delete(f"/platform-credentials/{credential_id}")
            st.success("Credential verwijderd.")
            st.rerun()


def manage_publications() -> None:
    products = api_get("/products")
    platforms = api_get("/platforms")
    if not products:
        st.info("Maak eerst een product aan.")
        return
    if not platforms:
        st.info("Maak eerst een platform aan.")
        return

    product_id = st.selectbox(
        "Product",
        [product["id"] for product in products],
        format_func=lambda x: product_name(products, x),
    )
    publications = api_get(f"/products/{product_id}/publications")

    with st.expander("Nieuwe platformpublicatie", expanded=False):
        available_platform_ids = [platform["id"] for platform in platforms]
        with st.form("create_publication"):
            platform_id = st.selectbox(
                "Platform",
                available_platform_ids,
                format_func=lambda x: next(p["name"] for p in platforms if p["id"] == x),
            )
            col1, col2 = st.columns(2)
            platform_title = col1.text_input("Platformtitel")
            platform_category = col2.text_input("Platformcategorie")
            platform_description = st.text_area("Platformomschrijving", height=120)
            col3, col4, col5 = st.columns(3)
            platform_tags = col3.text_input("Platformtags")
            platform_price_override = col4.number_input("Platformprijs override", min_value=0.0, step=0.50)
            platform_shipping_profile_id = col5.text_input("Verzendprofiel-ID")
            publication_status = st.selectbox(
                "Status",
                [
                    "niet_gepubliceerd",
                    "concept",
                    "klaar_voor_publicatie",
                    "gepubliceerd",
                    "synchronisatie_nodig",
                    "fout",
                    "gepauzeerd",
                    "gearchiveerd",
                ],
            )
            submitted = st.form_submit_button("Publicatie opslaan")

        if submitted:
            api_post(
                f"/products/{product_id}/publications",
                clean_payload(
                    {
                        "platform_id": platform_id,
                        "publication_status": publication_status,
                        "platform_title": platform_title,
                        "platform_description": platform_description,
                        "platform_category": platform_category,
                        "platform_tags": platform_tags,
                        "platform_price_override": platform_price_override or None,
                        "platform_shipping_profile_id": platform_shipping_profile_id,
                    }
                ),
            )
            st.success("Publicatie opgeslagen.")
            st.rerun()

    if publications:
        st.subheader("Publicaties")
        friendly_dataframe(publications)
        with st.expander("Publicatie bewerken en controleren", expanded=True):
            publication_id = st.selectbox(
                "Publicatie",
                [publication["id"] for publication in publications],
                format_func=lambda x: publication_label(publications, platforms, x),
            )
            publication = next(p for p in publications if p["id"] == publication_id)
            show_publication_status(publication)
            manage_publication_media(publication_id)
            edit_publication_form(publication, platforms)
            publication_actions(publication_id)
    else:
        st.info("Geen platformpublicaties voor dit product.")


def show_publication_status(publication: dict[str, Any]) -> None:
    col1, col2 = st.columns(2)
    col1.metric("Publicatiestatus", publication.get("publication_status") or "onbekend")
    col2.metric("Laatste synchronisatie", publication.get("last_synced_at") or "nog niet gesynchroniseerd")
    if publication.get("publication_status") == "synchronisatie_nodig":
        st.warning("Productinformatie is gewijzigd. Synchroniseer deze publicatie opnieuw wanneer je de wijziging wilt doorzetten.")
    if publication.get("last_error"):
        st.error(publication["last_error"])


def publication_label(publications: list[dict[str, Any]], platforms: list[dict[str, Any]], publication_id: int) -> str:
    publication = next(p for p in publications if p["id"] == publication_id)
    platform = next(p for p in platforms if p["id"] == publication["platform_id"])
    return f"{platform['name']} - {publication['publication_status']}"


def manage_publication_media(publication_id: int) -> None:
    st.subheader("Platformfoto's")
    st.caption("Kies welke centrale productfoto's voor deze platformpublicatie gebruikt worden en in welke volgorde.")
    media = api_get(f"/product-publications/{publication_id}/media")
    if not media:
        st.info("Geen productfoto's beschikbaar. Upload eerst foto's bij Productfoto's.")
        return

    selected_items = []
    for item in media:
        col1, col2, col3 = st.columns([1, 4, 1])
        selected = col1.checkbox("Gebruik", value=bool(item.get("selected")), key=f"pub_media_selected_{publication_id}_{item['id']}")
        label = item.get("alt_text") or item.get("file_path")
        image_bytes = uploaded_media_bytes(item.get("file_path"))
        if image_bytes:
            col2.image(image_bytes, caption=label, width=180)
        elif item.get("file_path", "").startswith(("http://", "https://")):
            col2.image(item["file_path"], caption=label, width=180)
        else:
            col2.write(label)
        sort_order = col3.number_input(
            "Volgorde",
            min_value=0,
            value=int(item.get("publication_sort_order") or 0),
            step=1,
            key=f"pub_media_order_{publication_id}_{item['id']}",
        )
        if selected:
            selected_items.append({"product_media_id": item["id"], "sort_order": sort_order, "active": True})

    if st.button("Platformfoto's opslaan", key=f"save_publication_media_{publication_id}"):
        api_put(f"/product-publications/{publication_id}/media", {"items": selected_items})
        st.success("Platformfoto's opgeslagen.")
        st.rerun()


def edit_publication_form(publication: dict[str, Any], platforms: list[dict[str, Any]]) -> None:
    status_options = [
        "niet_gepubliceerd",
        "concept",
        "klaar_voor_publicatie",
        "gepubliceerd",
        "synchronisatie_nodig",
        "fout",
        "gepauzeerd",
        "gearchiveerd",
    ]
    with st.form(f"edit_publication_{publication['id']}"):
        platform_ids = [platform["id"] for platform in platforms]
        platform_id = st.selectbox(
            "Platform",
            platform_ids,
            index=platform_ids.index(publication["platform_id"]),
            format_func=lambda x: next(p["name"] for p in platforms if p["id"] == x),
        )
        current_status = publication.get("publication_status")
        if current_status not in status_options:
            current_status = "niet_gepubliceerd"
        col1, col2, col3 = st.columns(3)
        publication_status = col1.selectbox("Status", status_options, index=status_options.index(current_status))
        external_product_id = col2.text_input("Extern product-ID", value=publication.get("external_product_id") or "")
        external_listing_id = col3.text_input("Extern listing-ID", value=publication.get("external_listing_id") or "")
        col4, col5 = st.columns(2)
        platform_title = col4.text_input("Platformtitel", value=publication.get("platform_title") or "")
        platform_category = col5.text_input("Platformcategorie", value=publication.get("platform_category") or "")
        platform_description = st.text_area(
            "Platformomschrijving", value=publication.get("platform_description") or "", height=120
        )
        col6, col7, col8 = st.columns(3)
        platform_tags = col6.text_input("Platformtags", value=publication.get("platform_tags") or "")
        platform_price_override = col7.number_input(
            "Platformprijs override",
            min_value=0.0,
            value=float(publication.get("platform_price_override") or 0),
            step=0.50,
        )
        platform_shipping_profile_id = col8.text_input(
            "Verzendprofiel-ID", value=publication.get("platform_shipping_profile_id") or ""
        )
        submitted = st.form_submit_button("Publicatie wijzigen")

    if submitted:
        api_put(
            f"/product-publications/{publication['id']}",
            clean_payload(
                {
                    "platform_id": platform_id,
                    "external_product_id": external_product_id,
                    "external_listing_id": external_listing_id,
                    "publication_status": publication_status,
                    "platform_title": platform_title,
                    "platform_description": platform_description,
                    "platform_category": platform_category,
                    "platform_tags": platform_tags,
                    "platform_price_override": platform_price_override or None,
                    "platform_shipping_profile_id": platform_shipping_profile_id,
                    "last_synced_at": publication.get("last_synced_at"),
                    "last_error": publication.get("last_error"),
                }
            ),
        )
        st.success("Publicatie bijgewerkt.")
        st.rerun()


def publication_actions(publication_id: int) -> None:
    col1, col2, col3, col4 = st.columns(4)
    if col1.button("Controleer publicatie"):
        show_publication_check(publication_id)
    if col2.button("Publiceer"):
        try:
            api_post(f"/product-publications/{publication_id}/publish")
            st.success("Publicatie gemarkeerd als gepubliceerd.")
            st.rerun()
        except requests.HTTPError as exc:
            st.error("Publicatiecontrole mislukt.")
            st.code(exc.response.text)
    if col3.button("Synchroniseer"):
        api_post(f"/product-publications/{publication_id}/sync")
        st.success("Publicatie gesynchroniseerd.")
        st.rerun()
    if col4.button("Pauzeer"):
        api_post(f"/product-publications/{publication_id}/pause")
        st.success("Publicatie gepauzeerd.")
        st.rerun()


def show_publication_check(publication_id: int) -> None:
    result = api_get(f"/product-publications/{publication_id}/check")
    if result["ready"]:
        st.success("Publicatie is klaar voor publicatie.")
    else:
        st.error("Publicatie is nog niet klaar.")
    if result["errors"]:
        st.write("Fouten")
        for error in result["errors"]:
            st.error(error)
    if result["warnings"]:
        st.write("Waarschuwingen")
        for warning in result["warnings"]:
            st.warning(warning)


def orders() -> None:
    page_header(
        "Orders",
        "Importeer, koppel SKU's, controleer voorraad en maak alleen printtaken voor tekorten.",
    )
    workflow_steps(
        "Werkvolgorde orderverwerking",
        [
            ("Import", "Haal orders op of maak dummydata"),
            ("Koppel", "Verbind SKU's aan varianten"),
            ("Voorraad", "Reserveer vrije voorraad"),
            ("Tekort", "Maak alleen printtaken voor tekort"),
            ("Print", "Verwerk resultaat"),
            ("Winst", "Bereken marge per order"),
        ],
    )
    tab_overview, tab_detail, tab_create, tab_import = st.tabs(["Overzicht", "Detail", "Nieuw", "Import"])

    with tab_overview:
        orders_data = api_get("/orders")
        order_items = api_get("/order-items")
        platforms = api_get("/platforms")
        open_orders = [order for order in orders_data if order.get("status") not in {"verzonden", "geannuleerd"}]
        needs_print = [
            order
            for order in orders_data
            if order.get("status") in {"deels_te_printen", "volledig_te_printen", "ingepland"}
        ]
        inventory_ready = [order for order in orders_data if order.get("status") == "volledig_uit_voorraad"]
        new_orders = [order for order in orders_data if order.get("status") == "nieuw"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("Nieuw", len(new_orders), "nog niet verwerkt")
        with col2:
            metric_card("Open", len(open_orders), "niet verzonden")
        with col3:
            metric_card("Uit voorraad", len(inventory_ready), "klaar voor vervolg")
        with col4:
            metric_card("Printwerk", len(needs_print), "tekort of ingepland")

        work_hint("Werk een order af in deze volgorde: SKU koppelen, voorraad controleren, printtaken maken, daarna printresultaat verwerken.")

        if orders_data:
            visible_orders = filter_by_status(orders_data, "orders_status")
            st.subheader("Orderrij")
            columns = st.columns(2)
            for index, order in enumerate(visible_orders[:8]):
                items_for_order = [item for item in order_items if item.get("order_id") == order.get("id")]
                quantity_to_print = sum(int(item.get("quantity_to_print") or 0) for item in items_for_order)
                quantity_from_inventory = sum(int(item.get("quantity_from_inventory") or 0) for item in items_for_order)
                next_step = "voorraad controleren"
                if order.get("status") in {"deels_te_printen", "volledig_te_printen"}:
                    next_step = "printtaken maken"
                elif order.get("status") == "ingepland":
                    next_step = "printresultaat verwerken"
                elif order.get("status") == "volledig_uit_voorraad":
                    next_step = "inpakken/verzenden"
                elif order.get("status") in {"verzonden", "geannuleerd"}:
                    next_step = "afgerond"
                with columns[index % 2]:
                    record_card(
                        order.get("internal_order_number"),
                        f"{platform_label(platforms, order.get('platform_id'))} - {order.get('customer_name') or 'Geen klantnaam'}",
                        order.get("status"),
                        [
                            ("Regels", len(items_for_order)),
                            ("Uit voorraad", quantity_from_inventory),
                            ("Te printen", quantity_to_print),
                            ("Volgende stap", next_step),
                        ],
                    )
            if len(visible_orders) > 8:
                st.caption(f"{len(visible_orders) - 8} extra orders staan in de tabel hieronder.")
            friendly_dataframe(
                [
                    {
                        "order": order.get("internal_order_number"),
                        "platform": platform_label(platforms, order.get("platform_id")),
                        "klant": order.get("customer_name"),
                        "datum": order.get("order_date"),
                        "status": order.get("status"),
                        "totaal": order.get("total_amount"),
                    }
                    for order in visible_orders
                ],
                ["order", "platform", "klant", "datum", "status", "totaal"],
            )
        else:
            st.info("Nog geen orders. Gebruik de dummy-import om de workflow te testen.")

        with st.expander("Orderregels tonen", expanded=False):
            if order_items:
                friendly_dataframe(enrich_order_items(order_items))
            else:
                st.info("Nog geen orderregels gevonden.")

    with tab_detail:
        manage_order_detail()

    with tab_create:
        create_order_forms()

    with tab_import:
        col1, col2 = st.columns(2)
        if col1.button("Dummy Etsy-import"):
            result = api_post("/orders/import/etsy")
            st.success(f"{result['status']} - order {result['order']['internal_order_number']}")
            st.rerun()
        if col2.button("Dummy Shopify-import"):
            result = api_post("/orders/import/shopify")
            st.success(f"{result['status']} - order {result['order']['internal_order_number']}")
            st.rerun()


def manage_order_detail() -> None:
    orders_data = api_get("/orders")
    if not orders_data:
        st.info("Geen orders gevonden.")
        return

    order_id = st.selectbox(
        "Order",
        [order["id"] for order in orders_data],
        format_func=lambda x: next(o["internal_order_number"] for o in orders_data if o["id"] == x),
    )
    order = api_get(f"/orders/{order_id}")
    platforms = api_get("/platforms")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", order.get("status") or "-")
    col2.metric("Platform", platform_label(platforms, order.get("platform_id")))
    col3.metric("Totaal", order.get("total_amount") or 0)
    col4.metric("Regels", len(order.get("items", [])))

    try:
        profit = api_get(f"/orders/{order_id}/profit")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Omzet", profit.get("sale_amount", 0))
        p2.metric("Filamentkosten", profit.get("filament_cost", 0))
        p3.metric("Platformkosten", profit.get("platform_fee", 0))
        p4.metric("Geschatte winst", profit.get("estimated_profit", 0))
    except Exception:
        st.info("Winstberekening nog niet beschikbaar voor deze order.")

    with st.form(f"edit_order_{order_id}"):
        col5, col6, col7 = st.columns(3)
        internal_order_number = col5.text_input("Intern ordernummer", value=order.get("internal_order_number") or "")
        external_order_id = col6.text_input("Extern order-ID", value=order.get("external_order_id") or "")
        platform_ids = [platform["id"] for platform in platforms]
        platform_id = col7.selectbox(
            "Platform",
            platform_ids,
            index=platform_ids.index(order["platform_id"]) if order.get("platform_id") in platform_ids else 0,
            format_func=lambda x: platform_label(platforms, x),
        )
        col8, col9, col10 = st.columns(3)
        customer_name = col8.text_input("Klantnaam", value=order.get("customer_name") or "")
        customer_email = col9.text_input("Klant e-mail", value=order.get("customer_email") or "")
        total_amount = col10.number_input("Totaalbedrag", min_value=0.0, value=float(order.get("total_amount") or 0), step=0.50)
        status_options = [
            "nieuw",
            "gecontroleerd",
            "volledig_uit_voorraad",
            "deels_te_printen",
            "volledig_te_printen",
            "ingepland",
            "geprint",
            "nabewerking",
            "ingepakt",
            "verzonden",
            "geannuleerd",
        ]
        current_status = order.get("status") if order.get("status") in status_options else "nieuw"
        col11, col12 = st.columns(2)
        status = col11.selectbox("Status", status_options, index=status_options.index(current_status))
        currency = col12.text_input("Valuta", value=order.get("currency") or "EUR")
        submitted = st.form_submit_button("Order wijzigen")

    if submitted:
        api_put(
            f"/orders/{order_id}",
            clean_payload(
                {
                    "internal_order_number": internal_order_number,
                    "platform_id": platform_id,
                    "external_order_id": external_order_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "order_date": order.get("order_date"),
                    "total_amount": total_amount,
                    "currency": currency,
                    "status": status,
                }
            ),
        )
        st.success("Order bijgewerkt.")
        st.rerun()

    if st.button("Orderregels koppelen via SKU"):
        result = api_post(f"/orders/{order_id}/link-items")
        st.success(f"{result['linked_count']} van {result['item_count']} regels gekoppeld.")
        st.rerun()

    if st.button("Voorraad controleren en reserveren"):
        result = api_post(f"/orders/{order_id}/process-inventory")
        st.success(f"Voorraad verwerkt. Nieuwe orderstatus: {result['order']['status']}")
        st.rerun()

    if st.button("Printtaken maken voor tekorten"):
        result = api_post(f"/orders/{order_id}/create-print-jobs")
        st.success(f"{len(result['created'])} printtaken aangemaakt, {len(result['updated'])} bijgewerkt.")
        st.rerun()

    if st.button("Winst opnieuw berekenen"):
        result = api_post(f"/orders/{order_id}/recalculate-profit")
        st.success(f"Geschatte winst: {result['estimated_profit']}")
        st.rerun()

    items = order.get("items", [])
    if items:
        st.subheader("Orderregels")
        friendly_dataframe(enrich_order_items(items))
    else:
        st.info("Deze order heeft nog geen orderregels.")


def create_order_forms() -> None:
    platforms = api_get("/platforms")
    orders_data = api_get("/orders")
    if not platforms:
        st.info("Maak eerst een platform aan.")
        return

    with st.expander("Nieuwe order", expanded=False):
        with st.form("create_order"):
            col1, col2, col3 = st.columns(3)
            internal_order_number = col1.text_input("Intern ordernummer")
            external_order_id = col2.text_input("Extern order-ID")
            platform_id = col3.selectbox(
                "Platform",
                [platform["id"] for platform in platforms],
                format_func=lambda x: platform_label(platforms, x),
            )
            col4, col5, col6 = st.columns(3)
            customer_name = col4.text_input("Klantnaam")
            customer_email = col5.text_input("Klant e-mail")
            total_amount = col6.number_input("Totaalbedrag", min_value=0.0, step=0.50)
            submitted = st.form_submit_button("Order opslaan")

        if submitted:
            if not internal_order_number or not external_order_id:
                st.error("Intern ordernummer en extern order-ID zijn verplicht.")
            else:
                api_post(
                    "/orders",
                    clean_payload(
                        {
                            "internal_order_number": internal_order_number,
                            "platform_id": platform_id,
                            "external_order_id": external_order_id,
                            "customer_name": customer_name,
                            "customer_email": customer_email,
                            "total_amount": total_amount or None,
                            "currency": "EUR",
                            "status": "nieuw",
                        }
                    ),
                )
                st.success("Order opgeslagen.")
                st.rerun()

    if not orders_data:
        st.info("Maak eerst een order aan voordat je orderregels toevoegt.")
        return

    with st.expander("Nieuwe orderregel", expanded=False):
        variants = api_get("/product-variants")
        with st.form("create_order_item"):
            order_id = st.selectbox(
                "Order",
                [order["id"] for order in orders_data],
                format_func=lambda x: next(o["internal_order_number"] for o in orders_data if o["id"] == x),
            )
            col1, col2, col3 = st.columns(3)
            sku = col1.text_input("SKU")
            quantity_ordered = col2.number_input("Aantal besteld", min_value=1, value=1, step=1)
            unit_sale_price = col3.number_input("Verkoopprijs per stuk", min_value=0.0, step=0.50)
            selected_variant_id = None
            if variants:
                variant_options = [0] + [variant["id"] for variant in variants]
                selected_variant_id = st.selectbox(
                    "Interne variant optioneel",
                    variant_options,
                    format_func=lambda x: "Automatisch via SKU" if x == 0 else variant_label(variants, x),
                )
            external_order_item_id = st.text_input("Extern orderregel-ID")
            submitted = st.form_submit_button("Orderregel opslaan")

        if submitted:
            variant = next((v for v in variants if v["id"] == selected_variant_id), None)
            api_post(
                "/order-items",
                clean_payload(
                    {
                        "order_id": order_id,
                        "product_id": variant.get("product_id") if variant else None,
                        "product_variant_id": variant.get("id") if variant else None,
                        "external_order_item_id": external_order_item_id,
                        "sku": sku or (variant.get("sku") if variant else None),
                        "quantity_ordered": quantity_ordered,
                        "unit_sale_price": unit_sale_price or None,
                        "inventory_status": "niet_op_voorraad",
                    }
                ),
            )
            st.success("Orderregel opgeslagen.")
            st.rerun()


def platform_label(platforms: list[dict[str, Any]], platform_id: int | None) -> str:
    platform = next((platform for platform in platforms if platform["id"] == platform_id), None)
    return platform["name"] if platform else "-"


def variant_label(variants: list[dict[str, Any]], variant_id: int) -> str:
    variant = next(variant for variant in variants if variant["id"] == variant_id)
    return f"{variant['sku']} - {variant['variant_name']}"


def enrich_order_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products = api_get("/products")
    variants = api_get("/product-variants")
    enriched = []
    for item in items:
        row = dict(item)
        product = next((product for product in products if product["id"] == item.get("product_id")), None)
        variant = next((variant for variant in variants if variant["id"] == item.get("product_variant_id")), None)
        row["product"] = product["name"] if product else "-"
        row["variant"] = variant["variant_name"] if variant else "-"
        row["linked"] = bool(product and variant)
        enriched.append(row)
    return enriched


def product_inventory() -> None:
    page_header(
        "Productvoorraad",
        "Beheer vrije voorraad, reserveringen en traceerbare voorraadbewegingen.",
    )
    workflow_steps(
        "Werkvolgorde voorraadbeheer",
        [
            ("Aanmaken", "Koppel voorraad aan een variant"),
            ("Vrij", "Controleer op voorraad min gereserveerd"),
            ("Reserveer", "Orders reserveren vrije voorraad"),
            ("Corrigeer", "Leg handmatige correcties vast"),
            ("Beweging", "Controleer audit voor/na"),
            ("Print", "Extra gelukte prints komen erbij"),
        ],
    )
    tab_overview, tab_create, tab_edit, tab_movements = st.tabs(["Overzicht", "Toevoegen", "Bewerken", "Bewegingen"])

    with tab_overview:
        inventory = api_get("/inventory/products")
        if inventory:
            friendly_dataframe(enrich_inventory_rows(inventory))
        else:
            st.info("Geen productvoorraad gevonden.")

    with tab_create:
        inventory_form()

    with tab_edit:
        inventory = api_get("/inventory/products")
        if not inventory:
            st.info("Geen productvoorraad gevonden.")
        else:
            inventory_id = st.selectbox(
                "Voorraadregel",
                [item["id"] for item in inventory],
                format_func=lambda x: inventory_label(inventory, x),
            )
            item = next(row for row in inventory if row["id"] == inventory_id)
            inventory_form(item)

    with tab_movements:
        st.subheader("Voorraadbewegingen")
        movements = api_get("/inventory/movements")
        if movements:
            friendly_dataframe(
                movements,
                [
                    "id",
                    "product_inventory_id",
                    "movement_type",
                    "quantity",
                    "source",
                    "reason",
                    "quantity_on_hand_before",
                    "quantity_on_hand_after",
                    "quantity_reserved_before",
                    "quantity_reserved_after",
                    "free_stock_before",
                    "free_stock_after",
                    "order_id",
                    "order_item_id",
                    "print_job_id",
                    "created_at",
                ],
            )
        else:
            st.info("Geen voorraadbewegingen gevonden.")


def inventory_form(item: dict[str, Any] | None = None) -> None:
    products = api_get("/products")
    variants = api_get("/product-variants")
    if not products or not variants:
        st.info("Maak eerst producten en varianten aan.")
        return

    form_key = f"inventory_{item['id']}" if item else "inventory_create"
    with st.form(form_key):
        variant_ids = [variant["id"] for variant in variants]
        selected_variant_id = item.get("product_variant_id") if item else variant_ids[0]
        if selected_variant_id not in variant_ids:
            selected_variant_id = variant_ids[0]
        product_variant_id = st.selectbox(
            "Productvariant",
            variant_ids,
            index=variant_ids.index(selected_variant_id),
            format_func=lambda x: variant_label(variants, x),
        )
        variant = next(v for v in variants if v["id"] == product_variant_id)
        col1, col2, col3, col4 = st.columns(4)
        color = col1.text_input("Kleur", value=(item.get("color") if item else variant.get("color")) or "")
        material = col2.text_input("Materiaal", value=(item.get("material") if item else variant.get("material")) or "")
        quantity_on_hand = col3.number_input(
            "Op voorraad",
            min_value=0,
            value=int(item.get("quantity_on_hand") if item else 0),
            step=1,
        )
        quantity_reserved = col4.number_input(
            "Gereserveerd",
            min_value=0,
            value=int(item.get("quantity_reserved") if item else 0),
            step=1,
        )
        col5, col6 = st.columns(2)
        minimum_stock_level = col5.number_input(
            "Minimumvoorraad",
            min_value=0,
            value=int(item.get("minimum_stock_level") if item else 0),
            step=1,
        )
        location = col6.text_input("Locatie", value=(item.get("location") if item else "") or "")
        submitted = st.form_submit_button("Voorraad opslaan")

    if submitted:
        payload = clean_payload(
            {
                "product_id": variant["product_id"],
                "product_variant_id": product_variant_id,
                "color": color,
                "material": material,
                "quantity_on_hand": quantity_on_hand,
                "quantity_reserved": quantity_reserved,
                "minimum_stock_level": minimum_stock_level,
                "location": location,
            }
        )
        if item:
            api_put(f"/inventory/products/{item['id']}", payload)
            st.success("Voorraadregel bijgewerkt.")
        else:
            api_post("/inventory/products", payload)
            st.success("Voorraadregel opgeslagen.")
        st.rerun()


def enrich_inventory_rows(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products = api_get("/products")
    variants = api_get("/product-variants")
    rows = []
    for item in inventory:
        row = dict(item)
        product = next((p for p in products if p["id"] == item.get("product_id")), None)
        variant = next((v for v in variants if v["id"] == item.get("product_variant_id")), None)
        row["product"] = product["name"] if product else "-"
        row["variant"] = variant["variant_name"] if variant else "-"
        row["free_stock"] = item.get("free_stock", item.get("quantity_on_hand", 0) - item.get("quantity_reserved", 0))
        rows.append(row)
    return rows


def inventory_label(inventory: list[dict[str, Any]], inventory_id: int) -> str:
    item = next(row for row in inventory if row["id"] == inventory_id)
    return f"#{item['id']} - variant {item['product_variant_id']} - vrij {item.get('free_stock', '-')}"


def filament() -> None:
    st.title("Filament")
    tab_create, tab_edit, tab_table = st.tabs(["Toevoegen", "Bewerken", "Overzicht"])

    with tab_create:
        with st.form("create_filament"):
            col1, col2, col3 = st.columns(3)
            brand = col1.text_input("Merk")
            material = col2.text_input("Materiaal", placeholder="PLA, PETG, TPU")
            color = col3.text_input("Kleur")
            col4, col5, col6 = st.columns(3)
            initial_weight_grams = col4.number_input("Startgewicht gram", min_value=1.0, value=1000.0, step=50.0)
            remaining_weight_grams = col5.number_input("Resterend gram", min_value=0.0, value=1000.0, step=50.0)
            purchase_price = col6.number_input("Aankoopprijs", min_value=0.0, value=20.0, step=0.50)
            col7, col8 = st.columns(2)
            minimum_remaining_grams = col7.number_input("Minimum gram", min_value=0.0, value=100.0, step=25.0)
            location = col8.text_input("Locatie")
            active = st.checkbox("Actief", value=True, key="create_filament_active")
            submitted = st.form_submit_button("Filamentrol opslaan")

        if submitted:
            if not brand or not material or not color:
                st.error("Merk, materiaal en kleur zijn verplicht.")
            elif remaining_weight_grams > initial_weight_grams:
                st.error("Resterend gewicht mag niet hoger zijn dan startgewicht.")
            else:
                api_post(
                    "/filament",
                    clean_payload(
                        {
                            "brand": brand,
                            "material": material,
                            "color": color,
                            "initial_weight_grams": initial_weight_grams,
                            "remaining_weight_grams": remaining_weight_grams,
                            "purchase_price": purchase_price,
                            "minimum_remaining_grams": minimum_remaining_grams,
                            "location": location,
                            "active": active,
                        }
                    ),
                )
                st.success("Filamentrol opgeslagen.")
                st.rerun()

    with tab_edit:
        spools = api_get("/filament")
        if not spools:
            st.info("Geen filamentrollen gevonden.")
        else:
            spool_id = st.selectbox(
                "Filamentrol",
                [spool["id"] for spool in spools],
                format_func=lambda x: next(
                    f"{s['brand']} - {s['material']} - {s['color']}" for s in spools if s["id"] == x
                ),
            )
            spool = next(s for s in spools if s["id"] == spool_id)
            with st.form("edit_filament"):
                col1, col2, col3 = st.columns(3)
                brand = col1.text_input("Merk", value=spool.get("brand") or "")
                material = col2.text_input("Materiaal", value=spool.get("material") or "")
                color = col3.text_input("Kleur", value=spool.get("color") or "")
                col4, col5, col6 = st.columns(3)
                initial_weight_grams = col4.number_input(
                    "Startgewicht gram", min_value=1.0, value=float(spool.get("initial_weight_grams") or 1000), step=50.0
                )
                remaining_weight_grams = col5.number_input(
                    "Resterend gram", min_value=0.0, value=float(spool.get("remaining_weight_grams") or 0), step=50.0
                )
                purchase_price = col6.number_input(
                    "Aankoopprijs", min_value=0.0, value=float(spool.get("purchase_price") or 0), step=0.50
                )
                col7, col8 = st.columns(2)
                minimum_remaining_grams = col7.number_input(
                    "Minimum gram", min_value=0.0, value=float(spool.get("minimum_remaining_grams") or 0), step=25.0
                )
                location = col8.text_input("Locatie", value=spool.get("location") or "")
                active = st.checkbox("Actief", value=bool(spool.get("active", True)), key="edit_filament_active")
                submitted = st.form_submit_button("Wijzigingen opslaan")

            if submitted:
                if not brand or not material or not color:
                    st.error("Merk, materiaal en kleur zijn verplicht.")
                elif remaining_weight_grams > initial_weight_grams:
                    st.error("Resterend gewicht mag niet hoger zijn dan startgewicht.")
                else:
                    api_put(
                        f"/filament/{spool_id}",
                        clean_payload(
                            {
                                "brand": brand,
                                "material": material,
                                "color": color,
                                "initial_weight_grams": initial_weight_grams,
                                "remaining_weight_grams": remaining_weight_grams,
                                "purchase_price": purchase_price,
                                "minimum_remaining_grams": minimum_remaining_grams,
                                "location": location,
                                "active": active,
                            }
                        ),
                    )
                    st.success("Filamentrol bijgewerkt.")
                    st.rerun()

    with tab_table:
        show_table("Filamentrollen", "/filament")


def costs_and_profit() -> None:
    st.title("Kosten en winst")
    tab_settings, tab_orders = st.tabs(["Kosteninstellingen", "Orderwinst"])

    with tab_settings:
        settings = api_get("/cost-settings")
        if settings:
            friendly_dataframe(settings)
            setting_id = st.selectbox(
                "Instelling bewerken",
                [setting["id"] for setting in settings],
                format_func=lambda x: next(s["setting_name"] for s in settings if s["id"] == x),
            )
            setting = next(s for s in settings if s["id"] == setting_id)
            with st.form("edit_cost_setting"):
                setting_name = st.text_input("Naam", value=setting.get("setting_name") or "")
                value = st.number_input("Waarde", value=float(setting.get("value") or 0), step=0.05, format="%.4f")
                submitted = st.form_submit_button("Instelling opslaan")
            if submitted:
                api_put(f"/cost-settings/{setting_id}", {"setting_name": setting_name, "value": value})
                st.success("Kosteninstelling bijgewerkt.")
                st.rerun()
        else:
            st.info("Geen kosteninstellingen gevonden.")

        with st.expander("Nieuwe kosteninstelling", expanded=False):
            with st.form("create_cost_setting"):
                setting_name = st.text_input("Naam")
                value = st.number_input("Waarde", value=0.0, step=0.05, format="%.4f")
                submitted = st.form_submit_button("Toevoegen")
            if submitted:
                if not setting_name:
                    st.error("Naam is verplicht.")
                else:
                    api_post("/cost-settings", {"setting_name": setting_name, "value": value})
                    st.success("Kosteninstelling opgeslagen.")
                    st.rerun()

    with tab_orders:
        orders_data = api_get("/orders")
        if not orders_data:
            st.info("Geen orders gevonden.")
            return
        order_id = st.selectbox(
            "Order",
            [order["id"] for order in orders_data],
            format_func=lambda x: next(o["internal_order_number"] for o in orders_data if o["id"] == x),
            key="profit_order_select",
        )
        if st.button("Orderwinst berekenen"):
            api_post(f"/orders/{order_id}/recalculate-profit")
        profit = api_get(f"/orders/{order_id}/profit")
        cols = st.columns(6)
        cols[0].metric("Omzet", profit.get("sale_amount", 0))
        cols[1].metric("Filament", profit.get("filament_cost", 0))
        cols[2].metric("Verpakking", profit.get("packaging_cost", 0))
        cols[3].metric("Platform", profit.get("platform_fee", 0))
        cols[4].metric("Verzending", profit.get("shipping_cost", 0))
        cols[5].metric("Winst", profit.get("estimated_profit", 0))
        st.json(profit)


def print_planning() -> None:
    page_header(
        "Printplanning",
        "Plan tekorten en extra voorraad per kleur, materiaal en batch voor gebruik in Bambu Studio.",
    )
    screen_purpose(
        [
            ("Tekorten", "Maak printtaken vanuit orders nadat vrije voorraad is gereserveerd."),
            ("Batchadvies", "Groepeer open printtaken automatisch op materiaal en kleur."),
            ("Resultaat", "Boek gelukt, mislukt, naar order en extra naar vrije voorraad."),
        ]
    )
    workflow_steps(
        "Werkvolgorde printplanning",
        [
            ("Tekorten", "Maak printtaken vanuit orders"),
            ("Advies", "Groepeer op materiaal en kleur"),
            ("Plan", "Pas aantallen bewust aan"),
            ("Batch", "Maak een Bambu-productielijst"),
            ("Resultaat", "Boek gelukt en mislukt"),
            ("Voorraad", "Extra prints gaan vrij op voorraad"),
        ],
    )
    tab_overview, tab_create, tab_suggestions, tab_edit, tab_complete, tab_batches = st.tabs(
        ["Overzicht", "Uit orders", "Batchadvies", "Plannen", "Resultaat", "Batches"]
    )

    with tab_overview:
        jobs = api_get("/print-jobs")
        if jobs:
            enriched_jobs = enrich_print_jobs(jobs)
            open_jobs = [job for job in enriched_jobs if job.get("status") not in {"verwerkt", "geannuleerd"}]
            active_jobs = [job for job in enriched_jobs if job.get("status") in {"gepland", "bezig"}]
            total_minutes = sum(int(job.get("estimated_print_time_minutes") or 0) for job in open_jobs)
            total_filament = sum(float(job.get("estimated_filament_grams") or 0) for job in open_jobs)
            extra_inventory = sum(int(job.get("extra_to_inventory") or 0) for job in open_jobs)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Open taken", len(open_jobs), "niet verwerkt")
            with col2:
                metric_card("Actief", len(active_jobs), "gepland of bezig")
            with col3:
                metric_card("Printtijd", f"{round(total_minutes / 60, 1)} u", "open werk")
            with col4:
                metric_card("Filament", f"{round(total_filament, 0)} g", f"{extra_inventory} extra voorraad")

            work_hint("Groepeer eerst op materiaal en kleur. Pas daarna aantallen aan als je bewust meer wilt printen voor vrije voorraad.")

            visible_jobs = filter_by_status(enriched_jobs, "print_jobs_status")
            material_options = ["Alle"] + sorted({str(job.get("material") or "-") for job in visible_jobs})
            material_choice = st.selectbox("Materiaalfilter", material_options, key="print_jobs_material")
            if material_choice != "Alle":
                visible_jobs = [job for job in visible_jobs if str(job.get("material") or "-") == material_choice]

            st.subheader("Printwachtrij")
            columns = st.columns(2)
            for index, job in enumerate(visible_jobs[:8]):
                with columns[index % 2]:
                    record_card(
                        f"#{job.get('id')} - {job.get('product')}",
                        job.get("variant"),
                        job.get("status"),
                        [
                            ("Kleur", job.get("color")),
                            ("Materiaal", job.get("material")),
                            ("Nodig", job.get("quantity_needed")),
                            ("Gepland", job.get("quantity_planned")),
                            ("Extra voorraad", job.get("extra_to_inventory")),
                            ("Tijd", f"{job.get('estimated_print_time_minutes') or 0} min"),
                        ],
                    )
            if len(visible_jobs) > 8:
                st.caption(f"{len(visible_jobs) - 8} extra printtaken staan in de tabel hieronder.")
            friendly_dataframe(
                [
                    {
                        "id": job.get("id"),
                        "product": job.get("product"),
                        "variant": job.get("variant"),
                        "kleur": job.get("color"),
                        "materiaal": job.get("material"),
                        "nodig": job.get("quantity_needed"),
                        "gepland": job.get("quantity_planned"),
                        "extra voorraad": job.get("extra_to_inventory"),
                        "tijd min": job.get("estimated_print_time_minutes"),
                        "filament g": job.get("estimated_filament_grams"),
                        "status": job.get("status"),
                    }
                    for job in visible_jobs
                ],
                [
                    "id",
                    "product",
                    "variant",
                    "kleur",
                    "materiaal",
                    "nodig",
                    "gepland",
                    "extra voorraad",
                    "tijd min",
                    "filament g",
                    "status",
                ],
            )
        else:
            st.info("Geen printtaken gevonden.")

    with tab_create:
        orders_data = api_get("/orders")
        if not orders_data:
            st.info("Geen orders gevonden.")
        else:
            order_id = st.selectbox(
                "Order",
                [order["id"] for order in orders_data],
                format_func=lambda x: next(o["internal_order_number"] for o in orders_data if o["id"] == x),
                key="print_jobs_order_select",
            )
            st.caption("Gebruik dit nadat voorraad is gecontroleerd. Alleen orderregels met een tekort krijgen een printtaak.")
            if st.button("Printtaken maken of bijwerken"):
                result = api_post(f"/orders/{order_id}/create-print-jobs")
                st.success(f"{len(result['created'])} aangemaakt, {len(result['updated'])} bijgewerkt.")
                st.rerun()

    with tab_suggestions:
        manage_batch_suggestions()

    with tab_edit:
        edit_print_job_form()

    with tab_complete:
        complete_print_job_form()

    with tab_batches:
        manage_print_batches()


def enrich_print_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products = api_get("/products")
    variants = api_get("/product-variants")
    rows = []
    for job in jobs:
        row = dict(job)
        product = next((product for product in products if product["id"] == job.get("product_id")), None)
        variant = next((variant for variant in variants if variant["id"] == job.get("product_variant_id")), None)
        row["product"] = product["name"] if product else "-"
        row["variant"] = variant["variant_name"] if variant else "-"
        row["extra_to_inventory"] = max(0, int(job.get("quantity_planned") or 0) - int(job.get("quantity_needed") or 0))
        rows.append(row)
    return rows


def edit_print_job_form() -> None:
    jobs = api_get("/print-jobs")
    if not jobs:
        st.info("Geen printtaken gevonden.")
        return

    job_id = st.selectbox(
        "Printtaak",
        [job["id"] for job in jobs],
        format_func=lambda x: print_job_label(jobs, x),
        key="edit_print_job_select",
    )
    job = next(item for item in jobs if item["id"] == job_id)
    with st.form(f"edit_print_job_{job_id}"):
        col1, col2, col3 = st.columns(3)
        quantity_needed = col1.number_input("Aantal nodig", min_value=0, value=int(job.get("quantity_needed") or 0), step=1)
        quantity_planned = col2.number_input(
            "Aantal gepland",
            min_value=0,
            value=int(job.get("quantity_planned") or 0),
            step=1,
        )
        status_options = ["nieuw", "gepland", "bezig", "geprint", "deels_mislukt", "mislukt", "verwerkt", "geannuleerd"]
        current_status = job.get("status") if job.get("status") in status_options else "nieuw"
        status = col3.selectbox("Status", status_options, index=status_options.index(current_status))
        col4, col5 = st.columns(2)
        estimated_print_time_minutes = col4.number_input(
            "Geschatte printtijd minuten",
            min_value=0,
            value=int(job.get("estimated_print_time_minutes") or 0),
            step=5,
        )
        estimated_filament_grams = col5.number_input(
            "Geschat filament gram",
            min_value=0,
            value=int(job.get("estimated_filament_grams") or 0),
            step=1,
        )
        submitted = st.form_submit_button("Printtaak bijwerken")

    if submitted:
        quantity_to_order = min(quantity_needed, quantity_planned)
        api_put(
            f"/print-jobs/{job_id}",
            clean_payload(
                {
                    "order_item_id": job.get("order_item_id"),
                    "product_id": job["product_id"],
                    "product_variant_id": job["product_variant_id"],
                    "color": job.get("color"),
                    "material": job.get("material"),
                    "quantity_needed": quantity_needed,
                    "quantity_planned": quantity_planned,
                    "quantity_succeeded": job.get("quantity_succeeded") or 0,
                    "quantity_failed": job.get("quantity_failed") or 0,
                    "quantity_to_order": quantity_to_order,
                    "quantity_to_inventory": max(0, quantity_planned - quantity_to_order),
                    "estimated_print_time_minutes": estimated_print_time_minutes or None,
                    "estimated_filament_grams": estimated_filament_grams or None,
                    "status": status,
                }
            ),
        )
        st.success("Printtaak bijgewerkt.")
        st.rerun()


def complete_print_job_form() -> None:
    jobs = api_get("/print-jobs")
    if not jobs:
        st.info("Geen printtaken gevonden.")
        return

    job_id = st.selectbox(
        "Printtaak",
        [job["id"] for job in jobs],
        format_func=lambda x: print_job_label(jobs, x),
        key="complete_print_job_select",
    )
    job = next(item for item in jobs if item["id"] == job_id)
    st.caption("Extra gelukte prints boven het orderaantal worden toegevoegd aan vrije productvoorraad.")
    with st.form(f"complete_print_job_{job_id}"):
        col1, col2, col3 = st.columns(3)
        quantity_succeeded = col1.number_input(
            "Aantal gelukt",
            min_value=0,
            value=int(job.get("quantity_planned") or job.get("quantity_needed") or 0),
            step=1,
        )
        quantity_failed = col2.number_input("Aantal mislukt", min_value=0, value=0, step=1)
        quantity_to_order = col3.number_input(
            "Aantal naar order",
            min_value=0,
            value=min(int(job.get("quantity_needed") or 0), int(job.get("quantity_planned") or 0)),
            step=1,
        )
        submitted = st.form_submit_button("Printresultaat verwerken")

    if submitted:
        if quantity_to_order > quantity_succeeded:
            st.error("Aantal naar order kan niet hoger zijn dan aantal gelukt.")
            return
        result = api_post(
            f"/print-jobs/{job_id}/complete",
            {
                "quantity_succeeded": quantity_succeeded,
                "quantity_failed": quantity_failed,
                "quantity_to_order": quantity_to_order,
            },
        )
        st.success(
            f"Resultaat verwerkt. Naar voorraad: {result['quantity_to_inventory']}, status: {result['status']}."
        )
        st.rerun()


def print_job_label(jobs: list[dict[str, Any]], job_id: int) -> str:
    job = next(item for item in jobs if item["id"] == job_id)
    return f"#{job['id']} - variant {job['product_variant_id']} - nodig {job['quantity_needed']} - {job['status']}"


def manage_batch_suggestions() -> None:
    suggestions = api_get("/planning/batch-suggestions")
    if not suggestions:
        st.info("Geen batchadvies beschikbaar. Maak eerst printtaken vanuit orders of voorraadadvies.")
        return

    work_hint("Batchadvies groepeert open printtaken met dezelfde kleur en hetzelfde materiaal. Kies een voorstel en maak daarna de export voor Bambu Studio.")
    for index, suggestion in enumerate(suggestions[:6]):
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                record_card(
                    suggestion.get("batch_name"),
                    suggestion.get("reason"),
                    "advies",
                    [
                        ("Taken", suggestion.get("job_count")),
                        ("Gepland", suggestion.get("quantity_planned")),
                        ("Voor orders", suggestion.get("quantity_to_order")),
                        ("Voor voorraad", suggestion.get("quantity_to_inventory")),
                        ("Printtijd", f"{round((suggestion.get('estimated_total_print_time_minutes') or 0) / 60, 1)} u"),
                        ("Filament", f"{suggestion.get('estimated_total_filament_grams') or 0} g"),
                    ],
                )
            with col2:
                batch_name = st.text_input(
                    "Batchnaam",
                    value=suggestion.get("batch_name") or "",
                    key=f"suggestion_batch_name_{index}",
                )
                if st.button("Batch maken", key=f"create_suggestion_batch_{index}", use_container_width=True):
                    api_post(
                        "/print-batches",
                        {
                            "batch_name": batch_name or suggestion.get("batch_name"),
                            "planned_date": None,
                            "material": suggestion.get("material"),
                            "color": suggestion.get("color"),
                            "print_job_ids": suggestion.get("print_job_ids", []),
                        },
                    )
                    st.success("Batch aangemaakt vanuit advies.")
                    st.rerun()
            with st.expander("Printtaken in dit advies", expanded=False):
                friendly_dataframe(
                    suggestion.get("products", []),
                    [
                        "print_job_id",
                        "product",
                        "variant",
                        "sku",
                        "quantity_planned",
                        "quantity_to_order",
                        "quantity_to_inventory",
                        "print_file_path",
                    ],
                )


def manage_print_batches() -> None:
    jobs = api_get("/print-jobs")
    batches = api_get("/print-batches")

    with st.expander("Nieuwe batch", expanded=False):
        if not jobs:
            st.info("Geen printtaken beschikbaar.")
        else:
            with st.form("create_print_batch"):
                batch_name = st.text_input("Batchnaam")
                planned_date = st.text_input("Geplande datum", placeholder="YYYY-MM-DD")
                col1, col2 = st.columns(2)
                material = col1.text_input("Materiaal filter/label")
                color = col2.text_input("Kleur filter/label")
                print_job_ids = st.multiselect(
                    "Printtaken",
                    [job["id"] for job in jobs],
                    format_func=lambda x: print_job_label(jobs, x),
                )
                submitted = st.form_submit_button("Batch opslaan")

            if submitted:
                if not batch_name:
                    st.error("Batchnaam is verplicht.")
                elif not print_job_ids:
                    st.error("Selecteer minimaal een printtaak.")
                else:
                    api_post(
                        "/print-batches",
                        clean_payload(
                            {
                                "batch_name": batch_name,
                                "planned_date": planned_date,
                                "material": material,
                                "color": color,
                                "print_job_ids": print_job_ids,
                            }
                        ),
                    )
                    st.success("Batch opgeslagen.")
                    st.rerun()

    if batches:
        st.subheader("Printbatches")
        friendly_dataframe(batches)
        batch_id = st.selectbox(
            "Batch",
            [batch["id"] for batch in batches],
            format_func=lambda x: next(f"{b['batch_name']} - {b['status']}" for b in batches if b["id"] == x),
        )
        batch = api_get(f"/print-batches/{batch_id}")
        if batch.get("items"):
            st.write("Batchregels")
            friendly_dataframe(batch["items"])
        if st.button("Export voor Bambu Studio maken"):
            result = api_post(f"/print-batches/{batch_id}/export")
            st.success(f"Export gemaakt: {result['export_dir']}")
            st.json(result["files"])
    else:
        st.info("Geen printbatches gevonden.")


def analytics() -> None:
    st.title("Trendanalyse")
    period_days = st.selectbox("Periode", [30, 60, 90], index=0, format_func=lambda value: f"Laatste {value} dagen")
    trends = api_get(f"/analytics/sales-trends?period_days={period_days}")
    top_products = api_get(f"/analytics/top-products?period_days={period_days}")
    top_colors = api_get(f"/analytics/top-colors?period_days={period_days}")
    top_materials = api_get(f"/analytics/top-materials?period_days={period_days}")

    total_quantity = sum(item.get("quantity_sold", 0) for item in trends)
    total_revenue = sum(item.get("revenue", 0) for item in trends)
    total_profit = sum(item.get("estimated_profit", 0) for item in trends)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Verkochte stuks", total_quantity)
    col2.metric("Omzet", round(total_revenue, 2))
    col3.metric("Geschatte winst", round(total_profit, 2))
    col4.metric("Productvarianten", len(trends))

    tab_trends, tab_products, tab_colors, tab_materials = st.tabs(
        ["Verkoop per variant", "Top producten", "Top kleuren", "Top materialen"]
    )

    with tab_trends:
        if trends:
            friendly_dataframe(trends)
            chart_data = pd.DataFrame(trends)[["variant", "quantity_sold"]].set_index("variant")
            st.bar_chart(chart_data)
        else:
            st.info("Geen verkoopdata gevonden voor deze periode.")

    with tab_products:
        if top_products:
            friendly_dataframe(top_products)
            st.bar_chart(pd.DataFrame(top_products)[["product", "quantity_sold"]].set_index("product"))
        else:
            st.info("Geen productdata gevonden.")

    with tab_colors:
        if top_colors:
            friendly_dataframe(top_colors)
            st.bar_chart(pd.DataFrame(top_colors)[["color", "quantity_sold"]].set_index("color"))
        else:
            st.info("Geen kleurdata gevonden.")

    with tab_materials:
        if top_materials:
            friendly_dataframe(top_materials)
            st.bar_chart(pd.DataFrame(top_materials)[["material", "quantity_sold"]].set_index("material"))
        else:
            st.info("Geen materiaaldata gevonden.")


def stock_advice() -> None:
    st.title("Voorraadadvies")
    tab_generate, tab_actions = st.tabs(["Genereren", "Adviezen"])

    with tab_generate:
        with st.form("generate_stock_recommendations"):
            col1, col2, col3 = st.columns(3)
            period_days = col1.selectbox("Analyseperiode", [30, 60, 90], index=0)
            weeks_ahead = col2.number_input("Vooruitkijken weken", min_value=1, value=1, step=1)
            safety_stock = col3.number_input("Veiligheidsvoorraad", min_value=0, value=2, step=1)
            submitted = st.form_submit_button("Voorraadadvies genereren")

        if submitted:
            result = api_post(
                "/stock-recommendations/generate",
                {
                    "period_days": period_days,
                    "weeks_ahead": weeks_ahead,
                    "safety_stock": safety_stock,
                },
            )
            st.success(f"{result['generated_count']} nieuw, {result['updated_count']} bijgewerkt.")
            st.rerun()

    with tab_actions:
        recommendations = api_get("/stock-recommendations")
        if not recommendations:
            st.info("Geen voorraadadviezen gevonden.")
            return

        friendly_dataframe(recommendations)
        recommendation_id = st.selectbox(
            "Advies",
            [item["id"] for item in recommendations],
            format_func=lambda x: recommendation_label(recommendations, x),
        )
        recommendation = next(item for item in recommendations if item["id"] == recommendation_id)
        col1, col2, col3 = st.columns(3)
        col1.metric("Vrije voorraad", recommendation.get("current_free_stock", 0))
        col2.metric("Verwachte verkoop", recommendation.get("expected_sales", 0))
        col3.metric("Advies extra printen", recommendation.get("recommended_print_quantity", 0))
        st.write(recommendation.get("reason") or "")

        with st.form(f"edit_stock_recommendation_{recommendation_id}"):
            edit_col1, edit_col2 = st.columns(2)
            edited_safety_stock = edit_col1.number_input(
                "Veiligheidsvoorraad aanpassen",
                min_value=0,
                value=int(recommendation.get("safety_stock") or 0),
                step=1,
            )
            edited_print_quantity = edit_col2.number_input(
                "Advies extra printen aanpassen",
                min_value=0,
                value=int(recommendation.get("recommended_print_quantity") or 0),
                step=1,
            )
            edit_reason = st.text_area("Reden aanpassing", value="Handmatig aangepast op basis van planning/voorraad.")
            edit_submitted = st.form_submit_button("Advies aanpassen")

        if edit_submitted:
            api_put(
                f"/stock-recommendations/{recommendation_id}",
                {
                    "safety_stock": edited_safety_stock,
                    "recommended_print_quantity": edited_print_quantity,
                    "reason": edit_reason,
                },
            )
            st.success("Advies aangepast.")
            st.rerun()

        action1, action2, action3 = st.columns(3)
        if action1.button("Accepteren"):
            api_post(f"/stock-recommendations/{recommendation_id}/accept")
            st.success("Advies geaccepteerd.")
            st.rerun()
        if action2.button("Negeren"):
            api_post(f"/stock-recommendations/{recommendation_id}/ignore")
            st.success("Advies genegeerd.")
            st.rerun()
        if action3.button("Omzetten naar printtaak"):
            result = api_post(f"/stock-recommendations/{recommendation_id}/convert-to-print-job")
            st.success(f"Printtaak #{result['id']} aangemaakt.")
            st.rerun()


def recommendation_label(recommendations: list[dict[str, Any]], recommendation_id: int) -> str:
    item = next(row for row in recommendations if row["id"] == recommendation_id)
    return f"#{item['id']} - {item.get('product')} / {item.get('variant')} - {item.get('recommended_print_quantity')} stuks - {item.get('status')}"


def live_readiness() -> None:
    page_header(
        "Live voorbereiding",
        "Controleer secrets, backups en verkoopplatformen voordat je echte Etsy- of Shopify-tokens gebruikt.",
        "gratis voorbereiding",
    )
    screen_purpose(
        [
            ("Secrets", "Controleer of tokens versleuteld en buiten de code worden bewaard."),
            ("Backups", "Zorg dat database, uploads en exports herstelbaar zijn voordat orders live gaan."),
            ("Koppelingen", "Bekijk per platform of mock/test/live veilig is voorbereid."),
        ]
    )

    tab_overview, tab_secrets, tab_backups, tab_connectors = st.tabs(
        ["Overzicht", "Secrets", "Backups", "Koppelingen"]
    )

    platforms = api_get("/platforms")
    statuses = []
    for platform in platforms:
        try:
            status = api_get(f"/platforms/{platform['id']}/connector-status")
        except Exception as exc:
            status = {"platform_type": platform.get("type"), "mode": "onbekend", "error": str(exc)}
        statuses.append({"platform": platform, "status": status})

    live_ready_count = sum(1 for item in statuses if item["status"].get("ready_for_live"))
    mock_count = sum(1 for item in statuses if item["status"].get("mode") == "mock")

    with tab_overview:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("Platformen", len(platforms), "aangemaakt")
        with col2:
            metric_card("Live compleet", live_ready_count, "credentials aanwezig")
        with col3:
            metric_card("Mockmodus", mock_count, "veilig testen zonder kosten")
        with col4:
            metric_card("Backups", "handmatig", "nog controleren op NAS")

        workflow_steps(
            "Veilige volgorde naar live",
            [
                ("1. Backup", "Database en uploads herstelbaar"),
                ("2. Secrets", "Encryptiesleutel vastzetten"),
                ("3. Testmodus", "Connectoren eerst mock/test"),
                ("4. Product", "Een volledig testproduct"),
                ("5. Order", "Een end-to-end testorder"),
                ("6. Live", "Pas daarna echte sync/import"),
            ],
        )
        work_hint("Gebruik dit scherm als checklist. Vul nog geen echte tokens in als backups en secrets niet duidelijk zijn.")

    with tab_secrets:
        st.subheader("Secrets checklist")
        friendly_dataframe(
            [
                {
                    "onderdeel": "CREDENTIAL_ENCRYPTION_KEY",
                    "status": "verplicht voor live",
                    "advies": "Gebruik een vaste key in NAS environment. Verander deze niet nadat tokens zijn opgeslagen.",
                },
                {
                    "onderdeel": "Platformtokens",
                    "status": "nog niet verplicht",
                    "advies": "Pas invoeren zodra je per platform klaar bent voor test/live.",
                },
                {
                    "onderdeel": ".env en compose",
                    "status": "controleren",
                    "advies": "Geen secrets in code, README, screenshots of logs bewaren.",
                },
                {
                    "onderdeel": "Connector modus",
                    "status": "mock is veilig",
                    "advies": "CONNECTORS_LIVE_MODE pas aanzetten na backup en testproduct.",
                },
            ]
        )
        if st.button("Nieuwe encryptiesleutel genereren tonen", use_container_width=True):
            result = api_get("/credentials/generate-key")
            st.warning("Bewaar deze key veilig. Als je hem later kwijtraakt, kun je opgeslagen tokens niet meer lezen.")
            st.code(result["key"])

    with tab_backups:
        st.subheader("Backup checklist")
        friendly_dataframe(
            [
                {
                    "onderdeel": "PostgreSQL database",
                    "status": "moet automatisch",
                    "advies": "Dagelijkse dump naar NAS backupmap, plus hersteltest.",
                },
                {
                    "onderdeel": "Productfoto's/uploads",
                    "status": "moet persistent",
                    "advies": "Volume backend_uploads meenemen in NAS backup.",
                },
                {
                    "onderdeel": "Bambu exports",
                    "status": "aanbevolen",
                    "advies": "Volume backend_exports meenemen als je exporthistorie wilt bewaren.",
                },
                {
                    "onderdeel": "Hersteltest",
                    "status": "nog doen",
                    "advies": "Minimaal een keer database + uploads terugzetten in testomgeving.",
                },
            ]
        )
        work_hint("Ik start hier geen backup-job, zodat er niets onverwachts of betaalds gebeurt. Dit is de live-checklist.")

    with tab_connectors:
        st.subheader("Platformkoppelingen")
        if not statuses:
            st.info("Nog geen platformen aangemaakt. Maak eerst Etsy en/of Shopify aan bij Platformpublicatie.")
        else:
            rows = []
            for item in statuses:
                platform = item["platform"]
                status = item["status"]
                rows.append(
                    {
                        "platform": platform.get("name"),
                        "type": platform.get("type"),
                        "modus": status.get("mode"),
                        "live_compleet": "ja" if status.get("ready_for_live") else "nee",
                        "vereist": ", ".join(status.get("required_credentials") or []),
                        "ontbreekt": ", ".join(status.get("missing_credentials") or []),
                        "ingesteld": ", ".join(status.get("configured_credentials") or []),
                    }
                )
            friendly_dataframe(rows)
        work_hint("Zolang de modus mock is, kun je veilig testen zonder externe kosten of echte platformacties.")


def ui_guide() -> None:
    page_header(
        "Handleiding",
        "Praktische klikroute voor de Streamlit UI: welk scherm gebruik je waarvoor?",
    )
    guide_path = next((path for path in UI_GUIDE_PATHS if path.exists()), None)
    if not guide_path:
        st.error("Handleiding niet gevonden.")
        return

    st.markdown(guide_path.read_text(encoding="utf-8"))


pages = {
    "Dashboard": dashboard,
    "Handleiding": ui_guide,
    "Live voorbereiding": live_readiness,
    "AI Product Assistent": ai_product_assistant,
    "Productcatalogus": product_catalog,
    "Productdetail": product_detail,
    "Productfoto's": product_media,
    "Platformpublicatie": platform_publication,
    "Orders": orders,
    "Productvoorraad": product_inventory,
    "Filament": filament,
    "Printplanning": print_planning,
    "Kosten en winst": costs_and_profit,
    "Trendanalyse": analytics,
    "Voorraadadvies": stock_advice,
}

navigation_groups = {
    "Overzicht": ["Dashboard", "Handleiding", "Live voorbereiding"],
    "Catalogus": ["AI Product Assistent", "Productcatalogus", "Productdetail", "Productfoto's", "Platformpublicatie"],
    "Operatie": ["Orders", "Productvoorraad", "Filament", "Printplanning"],
    "Sturing": ["Kosten en winst", "Trendanalyse", "Voorraadadvies"],
}

navigation_options = [
    {"group": group, "page": page, "label": f"{group} - {page}"}
    for group, group_pages in navigation_groups.items()
    for page in group_pages
]
navigation_labels = [item["label"] for item in navigation_options]
navigation_by_label = {item["label"]: item for item in navigation_options}
navigation_group_by_page = {item["page"]: item["group"] for item in navigation_options}

st.session_state.setdefault("selected_group", "Overzicht")
st.session_state.setdefault("selected_page_name", "Dashboard")


def select_page_from_top_navigation(widget_key: str) -> None:
    selected_navigation = navigation_by_label.get(st.session_state.get(widget_key))
    if not selected_navigation:
        return
    st.session_state.selected_group = selected_navigation["group"]
    st.session_state.selected_page_name = selected_navigation["page"]


with st.sidebar:
    st.markdown("### 3D Print Manager")
    st.caption("Centrale beheerlaag")

    try:
        api_status = requests.get(f"{API_BASE_URL}/health", timeout=3).ok
    except Exception:
        api_status = False
    st.markdown(
        f"API status: {status_badge('online' if api_status else 'offline')}",
        unsafe_allow_html=True,
    )

    selected_group = st.radio("Sectie", list(navigation_groups.keys()), horizontal=False, key="selected_group")
    if st.session_state.selected_page_name not in navigation_groups[selected_group]:
        st.session_state.selected_page_name = navigation_groups[selected_group][0]
    page_name = st.radio("Pagina", navigation_groups[selected_group], label_visibility="collapsed", key="selected_page_name")

    st.divider()
    st.caption(API_BASE_URL)

current_label = f"{navigation_group_by_page[st.session_state.selected_page_name]} - {st.session_state.selected_page_name}"
top_navigation_key = f"top_navigation_label_{slugify(current_label)}"
st.selectbox(
    "Pagina openen",
    navigation_labels,
    index=navigation_labels.index(current_label),
    key=top_navigation_key,
    on_change=select_page_from_top_navigation,
    args=(top_navigation_key,),
)

page_name = st.session_state.selected_page_name
pages[page_name]()
