"""Inmoenter / PANELIN-API integration for property feeds and CRM.

Supports two XML feed formats:
- XCP (Inmoenter proprietary format)
- KML3 (Kyero European standard)

Property documents are structured for optimal embedding quality:
~200-300 tokens per property in a structured Markdown-like format.
This minimizes vector store storage and per-query token costs.

Lead creation uses Inmoenter's RESTful contact management endpoints.
"""

import logging
from dataclasses import dataclass, field

import httpx
from lxml import etree

from .retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class Property:
    """Parsed property from Inmoenter XML feed."""

    id: str = ""
    title: str = ""
    description: str = ""
    price: str = ""
    currency: str = "EUR"
    location: str = ""
    property_type: str = ""
    operation: str = "Venta"
    bedrooms: int = 0
    bathrooms: int = 0
    area_m2: float = 0.0
    energy_cert: str = ""
    images: list[str] = field(default_factory=list)


async def fetch_property_feed(
    feed_url: str,
    api_key: str,
) -> list[Property]:
    """Download and parse property XML feed from Inmoenter.

    Supports both XCP and KML3 formats. Auto-detects format
    from root element name.

    Args:
        feed_url: Full URL to the XML feed endpoint.
        api_key: Inmoenter API key (passed as query parameter).

    Returns:
        List of parsed Property objects.
    """
    separator = "&" if "?" in feed_url else "?"
    url = f"{feed_url}{separator}api_key={api_key}"

    async def _do_fetch() -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    try:
        xml_bytes = await retry_with_backoff(_do_fetch, max_retries=3)
    except Exception:
        logger.exception("Failed to fetch property feed from %s", feed_url)
        return []

    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        logger.exception("Failed to parse XML feed")
        return []

    root_tag = etree.QName(root).localname.lower() if root.tag else ""

    if "kyero" in root_tag or root.find(".//property") is not None:
        return _parse_kyero_kml3(root)
    return _parse_xcp(root)


def _parse_xcp(root: etree._Element) -> list[Property]:
    """Parse Inmoenter XCP format XML."""
    properties: list[Property] = []
    for elem in root.iter("inmueble", "property", "ad"):
        prop = Property(
            id=_text(elem, "id", "referencia", "ref"),
            title=_text(elem, "titulo", "title", "name"),
            description=_text(elem, "descripcion", "description", "desc"),
            price=_text(elem, "precio", "price"),
            currency=_text(elem, "moneda", "currency") or "EUR",
            location=_build_location(elem),
            property_type=_text(elem, "tipo", "type", "property_type"),
            operation=_text(elem, "operacion", "operation") or "Venta",
            bedrooms=_int(elem, "habitaciones", "bedrooms", "rooms"),
            bathrooms=_int(elem, "banos", "bathrooms"),
            area_m2=_float(elem, "superficie", "area", "size"),
            energy_cert=_text(elem, "certificacion_energetica", "energy_cert"),
            images=_images(elem),
        )
        if prop.id:
            properties.append(prop)
    return properties


def _parse_kyero_kml3(root: etree._Element) -> list[Property]:
    """Parse Kyero KML3 format XML."""
    properties: list[Property] = []
    for elem in root.iter("property"):
        prop = Property(
            id=_text(elem, "id", "ref"),
            title=_text(elem, "title"),
            description=_text(elem, "desc"),
            price=_text(elem, "price"),
            currency=_text(elem, "currency") or "EUR",
            location=_build_location(elem),
            property_type=_text(elem, "type"),
            operation="Alquiler" if _text(elem, "leasehold") else "Venta",
            bedrooms=_int(elem, "beds"),
            bathrooms=_int(elem, "baths"),
            area_m2=_float(elem, "surface_area", "built"),
            energy_cert=_text(elem, "energy_rating", "energy_cert"),
            images=_images(elem),
        )
        if prop.id:
            properties.append(prop)
    return properties


def _text(elem: etree._Element, *tag_names: str) -> str:
    """Extract text from the first matching child element."""
    for tag in tag_names:
        child = elem.find(f".//{tag}")
        if child is not None and child.text:
            return child.text.strip()
    return ""


def _int(elem: etree._Element, *tag_names: str) -> int:
    """Extract integer from the first matching child element."""
    val = _text(elem, *tag_names)
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _float(elem: etree._Element, *tag_names: str) -> float:
    """Extract float from the first matching child element."""
    val = _text(elem, *tag_names)
    try:
        return float(val.replace(",", "."))
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _build_location(elem: etree._Element) -> str:
    """Build location string from various address elements."""
    parts: list[str] = []
    for tag in (
        "localidad", "town", "city",
        "provincia", "province",
        "region", "country", "pais",
    ):
        val = _text(elem, tag)
        if val:
            parts.append(val)
    return ", ".join(parts) or _text(elem, "location", "ubicacion")


def _images(elem: etree._Element) -> list[str]:
    """Extract image URLs from property element (max 10)."""
    urls: list[str] = []
    for img_elem in elem.iter("image", "imagen", "foto", "url"):
        if img_elem.text and img_elem.text.strip().startswith("http"):
            urls.append(img_elem.text.strip())
        url_child = img_elem.find("url")
        if url_child is not None and url_child.text:
            urls.append(url_child.text.strip())
    return urls[:10]


def transform_properties_to_documents(
    properties: list[Property],
) -> list[tuple[str, str]]:
    """Convert properties to embedding-optimized text documents.

    Each document uses ~200-300 tokens in structured Markdown.
    This maximizes retrieval precision while minimizing storage
    and per-query token costs.

    Returns:
        List of (filename, content) tuples.
    """
    documents: list[tuple[str, str]] = []
    for prop in properties:
        content = (
            f"# Propiedad: {prop.title or 'Sin título'}\n"
            f"ID: {prop.id}\n"
            f"Tipo: {prop.property_type} | Operación: {prop.operation}\n"
            f"Precio: {prop.price} {prop.currency}\n"
            f"Ubicación: {prop.location}\n"
            f"Superficie: {prop.area_m2} m² | "
            f"Habitaciones: {prop.bedrooms} | Baños: {prop.bathrooms}\n"
        )
        if prop.energy_cert:
            content += f"Certificación energética: {prop.energy_cert}\n"
        if prop.description:
            desc = prop.description[:500]
            content += f"\nDescripción: {desc}\n"

        filename = f"property_{prop.id}.txt"
        documents.append((filename, content))

    return documents


async def create_lead_in_crm(
    base_url: str,
    api_key: str,
    client_data: dict,
) -> str | None:
    """Create a qualified lead in Inmoenter CRM.

    Args:
        base_url: Inmoenter API base URL.
        api_key: API authentication key.
        client_data: Dict with keys: name, phone, email,
                     budget, desired_location, urgency, notes.

    Returns:
        Lead ID from CRM on success, None on failure.
    """

    async def _do_create() -> str | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/api/contacts",
                json=client_data,
                params={"api_key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("id") or data.get("lead_id") or data.get("contact_id")

    try:
        return await retry_with_backoff(_do_create, max_retries=2)
    except Exception:
        logger.exception("Failed to create lead in Inmoenter CRM")
        return None
