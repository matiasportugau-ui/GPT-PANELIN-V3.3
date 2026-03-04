"""Tests for BMC Uruguay product knowledge base sync.

Tests loading products from JSON KB files (bromyros_pricing_master.json,
BMC_Base_Conocimiento_GPT-2.json) and transforming them to embedding
documents for OpenAI Vector Store.
"""

import json
import tempfile
from pathlib import Path

import pytest

from whatsapp_bot.panelin_sync import (
    Product,
    load_products_from_kb,
    load_products_from_pricing,
    transform_products_to_documents,
)


SAMPLE_PRICING_JSON = {
    "data": {
        "metadata": {
            "total_products": 3,
            "currency": "USD",
            "iva_rate": 0.22,
        },
        "indices": {
            "by_sku": {
                "IROOF50": {
                    "familia": "ISOROOF",
                    "sub_familia": "PIR",
                    "tipo": "Panel",
                },
                "IROOF100": {
                    "familia": "ISOROOF",
                    "sub_familia": "PIR",
                    "tipo": "Panel",
                },
                "IDEC100": {
                    "familia": "ISODEC",
                    "sub_familia": "EPS",
                    "tipo": "Panel",
                },
            }
        },
    }
}

SAMPLE_KB_JSON = {
    "meta": {
        "nombre": "BMC Uruguay - Sistema Unificado",
        "version": "6.0",
    },
    "products": {
        "ISODEC_EPS": {
            "nombre_comercial": "Isodec / Isowall (EPS)",
            "tipo": "cubierta_pesada",
            "ancho_util": 1.12,
            "sistema_fijacion": "varilla_tuerca",
            "espesores": {
                "100": {
                    "autoportancia": 5.5,
                    "precio": 46.07,
                    "coeficiente_termico": 0.035,
                },
                "50": {
                    "autoportancia": 4.0,
                    "precio": 32.50,
                },
            },
        },
        "ISOROOF_PIR": {
            "nombre_comercial": "Isoroof (PIR)",
            "tipo": "cubierta_liviana",
            "ancho_util": 1.0,
            "sistema_fijacion": "tornillo_autoperforante",
            "espesores": {
                "50": {
                    "autoportancia": 3.5,
                    "precio": 38.20,
                },
            },
        },
    },
}


class TestLoadProductsFromPricing:
    """Tests for loading products from bromyros_pricing_master.json."""

    def test_loads_from_indices(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_PRICING_JSON, f)
            f.flush()

            products = load_products_from_pricing(f.name)

        assert len(products) == 3
        skus = {p.sku for p in products}
        assert "IROOF50" in skus
        assert "IROOF100" in skus
        assert "IDEC100" in skus

    def test_returns_empty_for_missing_file(self):
        products = load_products_from_pricing("/nonexistent.json")
        assert products == []


class TestLoadProductsFromKB:
    """Tests for loading products from BMC_Base_Conocimiento_GPT-2.json."""

    def test_loads_product_families(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_KB_JSON, f)
            f.flush()

            products = load_products_from_kb(f.name)

        # 2 espesores from ISODEC_EPS + 1 from ISOROOF_PIR = 3 variants
        assert len(products) == 3

    def test_parses_product_fields(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_KB_JSON, f)
            f.flush()

            products = load_products_from_kb(f.name)

        # Find the ISODEC_EPS 100mm variant
        isodec_100 = next(
            (p for p in products if "100" in p.sku and "ISODEC" in p.sku),
            None,
        )
        assert isodec_100 is not None
        assert isodec_100.thickness_mm == 100
        assert isodec_100.price_usd == 46.07
        assert isodec_100.autoportancia_m == 5.5
        assert isodec_100.width_m == 1.12
        assert "Isodec" in isodec_100.name

    def test_calculates_iva(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_KB_JSON, f)
            f.flush()

            products = load_products_from_kb(f.name)

        isodec_100 = next(
            (p for p in products if "100" in p.sku and "ISODEC" in p.sku),
            None,
        )
        assert isodec_100 is not None
        expected_iva = round(46.07 * 1.22, 2)
        assert isodec_100.price_with_iva == expected_iva

    def test_returns_empty_for_missing_file(self):
        products = load_products_from_kb("/nonexistent.json")
        assert products == []


class TestTransformProductsToDocuments:
    """Tests for product → embedding document transformation."""

    def test_generates_structured_text(self):
        prod = Product(
            sku="ISODEC_EPS_100",
            name="Isodec EPS 100mm",
            family="ISODEC_EPS",
            product_type="cubierta_pesada",
            thickness_mm=100,
            price_usd=46.07,
            price_with_iva=56.21,
            unit="m2",
            width_m=1.12,
            autoportancia_m=5.5,
            core="EPS",
            description="Panel cubierta pesada con fijacion varilla_tuerca",
        )
        docs = transform_products_to_documents([prod])

        assert len(docs) == 1
        filename, content = docs[0]
        assert filename == "product_ISODEC_EPS_100.txt"
        assert "Isodec EPS 100mm" in content
        assert "46.07" in content
        assert "IVA 22%" in content
        assert "100 mm" in content
        assert "5.5 m" in content

    def test_empty_products_list(self):
        docs = transform_products_to_documents([])
        assert docs == []

    def test_minimal_product(self):
        """Product with only required fields should not crash."""
        prod = Product(sku="TEST-001", name="Test Product")
        docs = transform_products_to_documents([prod])
        assert len(docs) == 1
        filename, content = docs[0]
        assert filename == "product_TEST-001.txt"
        assert "Test Product" in content
