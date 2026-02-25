"""Tests for Inmoenter XML parsing and document transformation.

Uses inline XML strings as fixtures — no external files needed.
Tests both XCP (Inmoenter proprietary) and KML3 (Kyero European) formats.
"""

import pytest
from lxml import etree

from whatsapp_bot.inmoenter_sync import (
    Property,
    _parse_xcp,
    _parse_kyero_kml3,
    transform_properties_to_documents,
)

XCP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
  <inmueble>
    <id>INM-001</id>
    <titulo>Ático en Marbella</titulo>
    <descripcion>Luminoso ático con vistas al mar</descripcion>
    <precio>285000</precio>
    <moneda>EUR</moneda>
    <localidad>Marbella</localidad>
    <provincia>Málaga</provincia>
    <tipo>Ático</tipo>
    <operacion>Venta</operacion>
    <habitaciones>2</habitaciones>
    <banos>2</banos>
    <superficie>95</superficie>
    <certificacion_energetica>B</certificacion_energetica>
  </inmueble>
  <inmueble>
    <id>INM-002</id>
    <titulo>Piso en Madrid</titulo>
    <precio>220000</precio>
    <localidad>Madrid</localidad>
    <tipo>Piso</tipo>
    <habitaciones>3</habitaciones>
    <banos>1</banos>
    <superficie>80</superficie>
  </inmueble>
</root>"""

KML3_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kyero>
  <property>
    <id>KYR-002</id>
    <title>Villa en Costa del Sol</title>
    <desc>Amplia villa con piscina privada</desc>
    <price>450000</price>
    <currency>EUR</currency>
    <town>Estepona</town>
    <province>Málaga</province>
    <type>Villa</type>
    <beds>4</beds>
    <baths>3</baths>
    <surface_area>250</surface_area>
    <energy_rating>C</energy_rating>
  </property>
</kyero>"""


class TestParseXCP:
    """Tests for Inmoenter XCP format XML parsing."""

    def test_parses_all_properties(self):
        root = etree.fromstring(XCP_XML)
        props = _parse_xcp(root)
        assert len(props) == 2

    def test_parses_property_fields(self):
        root = etree.fromstring(XCP_XML)
        props = _parse_xcp(root)
        p = props[0]
        assert p.id == "INM-001"
        assert p.title == "Ático en Marbella"
        assert p.price == "285000"
        assert p.currency == "EUR"
        assert p.bedrooms == 2
        assert p.bathrooms == 2
        assert p.area_m2 == 95.0
        assert p.energy_cert == "B"
        assert "Marbella" in p.location
        assert p.operation == "Venta"

    def test_missing_optional_fields(self):
        """Properties without all fields should use defaults."""
        root = etree.fromstring(XCP_XML)
        props = _parse_xcp(root)
        p = props[1]  # INM-002 — missing energy cert, description
        assert p.id == "INM-002"
        assert p.energy_cert == ""
        assert p.description == ""


class TestParseKML3:
    """Tests for Kyero KML3 format XML parsing."""

    def test_parses_kyero_format(self):
        root = etree.fromstring(KML3_XML)
        props = _parse_kyero_kml3(root)
        assert len(props) == 1
        p = props[0]
        assert p.id == "KYR-002"
        assert p.title == "Villa en Costa del Sol"
        assert p.bedrooms == 4
        assert p.bathrooms == 3
        assert p.area_m2 == 250.0
        assert p.energy_cert == "C"
        assert "Estepona" in p.location


class TestTransformDocuments:
    """Tests for property → text document transformation."""

    def test_generates_structured_text(self):
        prop = Property(
            id="T-001",
            title="Piso centro",
            price="180000",
            currency="EUR",
            location="Madrid",
            property_type="Piso",
            operation="Venta",
            bedrooms=3,
            bathrooms=1,
            area_m2=80.0,
            description="Bonito piso reformado en pleno centro",
        )
        docs = transform_properties_to_documents([prop])
        assert len(docs) == 1
        filename, content = docs[0]
        assert filename == "property_T-001.txt"
        assert "Piso centro" in content
        assert "180000 EUR" in content
        assert "Madrid" in content
        assert "Habitaciones: 3" in content
        assert "Baños: 1" in content
        assert "80.0 m²" in content
        assert "Bonito piso" in content

    def test_truncates_long_descriptions(self):
        """Descriptions > 500 chars should be truncated to save tokens."""
        prop = Property(
            id="T-002",
            title="Test",
            description="A" * 1000,
        )
        docs = transform_properties_to_documents([prop])
        _, content = docs[0]
        # 500 chars of description + prefix "Descripción: " + newline
        assert "A" * 500 in content
        assert "A" * 501 not in content

    def test_empty_properties_list(self):
        docs = transform_properties_to_documents([])
        assert docs == []
