"""Tests for morning audit dedupe and row mapping helpers."""

from morning_audit import build_duplicate_key, build_sheet_row, normalize_date_ddmm, normalize_text


def test_normalize_text_removes_accents_and_spaces() -> None:
    assert normalize_text("  José   Pérez  ") == "jose perez"


def test_normalize_date_ddmm_accepts_multiple_formats() -> None:
    assert normalize_date_ddmm("2026-03-02") == "02-03"
    assert normalize_date_ddmm("02/03/2026") == "02-03"
    assert normalize_date_ddmm("02-03") == "02-03"


def test_duplicate_key_normalizes_cliente_and_origen() -> None:
    key_a = build_duplicate_key("José Pérez", "2026-03-02", "ml")
    key_b = build_duplicate_key("jose   perez", "02-03", "ML")
    assert key_a == key_b


def test_build_sheet_row_respects_atead_contract() -> None:
    row = build_sheet_row(
        {
            "cliente": "Cliente Uno",
            "origen": "wa",
            "telefono": "099123123",
            "direccion": "Montevideo",
            "consulta": "Necesito cotización",
            "fecha": "2026-03-02",
        }
    )
    assert len(row) == 8
    assert row[0] == ""
    assert row[1] == "Pendiente"
    assert row[2] == "02-03"
    assert row[3] == "Cliente Uno"
    assert row[4] == "WA"
    assert row[5] == "099123123"
    assert row[6] == "Montevideo"
    assert row[7] == "Necesito cotización"
