"""Slab boundaries for TY2026 and TY2027, checked against the rules files."""

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from app.core.tax_engine import (
    TaxError,
    compare,
    freelancer,
    load_rules,
    property_tax,
    salary,
)

RULES = Path(__file__).resolve().parents[2] / "app" / "core" / "tax_rules"

# (from, to, fixed, rate). `to` is inclusive. These are the ordinance tables, not the engine.
SALARY = {
    "TY2026": [
        (0, 600_000, 0, "0"),
        (600_000, 1_200_000, 0, "0.01"),
        (1_200_000, 2_200_000, 6_000, "0.11"),
        (2_200_000, 3_200_000, 116_000, "0.23"),
        (3_200_000, 4_100_000, 346_000, "0.30"),
        (4_100_000, None, 616_000, "0.35"),
    ],
    "TY2027": [
        (0, 600_000, 0, "0"),
        (600_000, 1_200_000, 0, "0.01"),
        (1_200_000, 2_200_000, 6_000, "0.11"),
        (2_200_000, 3_200_000, 116_000, "0.20"),
        (3_200_000, 4_100_000, 316_000, "0.25"),
        (4_100_000, 5_600_000, 541_000, "0.29"),
        (5_600_000, 7_000_000, 976_000, "0.32"),
        (7_000_000, None, 1_424_000, "0.35"),
    ],
}
SURCHARGE = {"TY2026": "0.09", "TY2027": "0"}


def _rupees(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _expected_salary(tax_year: str, income: int) -> int:
    chosen = SALARY[tax_year][-1]
    for slab in SALARY[tax_year]:
        if slab[1] is None or income <= slab[1]:
            chosen = slab
            break
    start, _end, fixed, rate = chosen
    tax = _rupees(Decimal(fixed) + Decimal(rate) * Decimal(income - start))
    surcharge = Decimal(SURCHARGE[tax_year])
    if income > 10_000_000 and surcharge > 0:
        tax += _rupees(surcharge * Decimal(tax))
    return tax


def _boundaries(tax_year: str) -> list[int]:
    incomes = {0}
    for _start, end, _fixed, _rate in SALARY[tax_year]:
        if end is None:
            continue
        incomes.update({end - 1, end, end + 1})
    incomes.update({9_999_999, 10_000_000, 10_000_001})
    return sorted(incomes)


def test_rules_files_match_the_ordinance_tables():
    for tax_year, slabs in SALARY.items():
        raw = json.loads((RULES / f"{tax_year.lower()}.json").read_text(encoding="utf-8"))
        encoded = [
            (row["from"], row["to"], row["fixed"], row["rate"]) for row in raw["salary"]["slabs"]
        ]
        assert encoded == slabs
        assert raw["surcharge"]["salaried"]["rate_on_tax"] == SURCHARGE[tax_year]
        assert raw["salary"]["source"]["ref"]
        assert raw["surcharge"]["source"]["ref"]


@pytest.mark.parametrize("tax_year", ["TY2026", "TY2027"])
def test_salary_just_below_at_and_above_every_boundary(tax_year: str):
    for income in _boundaries(tax_year):
        result = salary(tax_year, income)
        assert result["total_tax"] == _expected_salary(tax_year, income)


def test_ty2026_surcharge_starts_above_ten_million():
    below = salary("TY2026", 10_000_000)
    above = salary("TY2026", 10_000_001)
    assert all("4AB" not in line["label"] for line in below["breakdown"])
    assert above["breakdown"][-1]["label"] == "Section 4AB surcharge"
    assert above["total_tax"] > below["total_tax"]


def test_ty2027_salary_has_no_surcharge_line():
    result = salary("TY2027", 12_000_000)
    assert all("4AB" not in line["label"] for line in result["breakdown"])
    assert result["compared_to"]["tax_year"] == "TY2026"
    assert result["compared_to"]["difference"] != 0


def test_monthly_salary_is_twelve_times_the_annual_input():
    annual = salary("TY2027", 1_200_000)
    assert annual["total_tax"] == 6_000
    assert annual["monthly_tax"] == 500
    assert annual["net_annual"] == 1_194_000


@pytest.mark.parametrize("tax_year", ["TY2026", "TY2027"])
@pytest.mark.parametrize("side", ["purchase", "sale"])
def test_property_value_boundaries(tax_year: str, side: str):
    rules = load_rules(tax_year)
    key = "property_purchase" if side == "purchase" else "property_sale"
    bands = rules["withholding"][key]["bands"]
    for band in bands:
        if band["to"] is None:
            continue
        for value in (band["to"] - 1, band["to"], band["to"] + 1):
            expected_band = next(
                item for item in bands if item["to"] is None or value <= item["to"]
            )
            for status in ("filer", "non_filer"):
                result = property_tax(tax_year, side, value, status)
                expected = _rupees(Decimal(expected_band[status]) * Decimal(value))
                assert result["total_tax"] == expected


def test_ty2026_property_has_a_late_filer_rate_and_ty2027_does_not():
    late = property_tax("TY2026", "sale", 50_000_000, "late_filer")
    assert late["total_tax"] == 3_750_000
    with pytest.raises(TaxError) as raised:
        property_tax("TY2027", "purchase", 50_000_000, "late_filer")
    assert raised.value.code == "invalid_request"


def test_freelancer_regimes_use_the_cited_rates():
    pseb = freelancer("TY2026", 1_000_000, "pseb_export", "filer")
    other = freelancer("TY2026", 1_000_000, "export_services", "non_filer")
    domestic = freelancer("TY2027", 1_000_000, "local_services", "non_filer")
    assert pseb["total_tax"] == 2_500
    assert other["total_tax"] == 20_000
    assert domestic["total_tax"] == 80_000
    assert pseb["inputs"]["regime"] == "pseb_export"


def test_filer_comparison_rejects_an_unknown_type_and_prices_a_known_one():
    with pytest.raises(TaxError) as raised:
        compare("TY2027", [{"type": "plot", "amount": 100}])
    assert raised.value.code == "unknown_transaction_type"
    assert "property_purchase" in raised.value.details["valid"]

    result = compare(
        "TY2027",
        [
            {"type": "dividend", "amount": 100_000},
            {"type": "vehicle_registration", "amount": 2_000_000, "engine_cc": 1300},
        ],
    )
    assert result["rows"][0]["filer_tax"] == 15_000
    assert result["rows"][0]["non_filer_tax"] == 30_000
    assert result["rows"][0]["late_filer_tax"] is None
    assert result["rows"][1]["filer_tax"] == 30_000
    assert result["savings"] == result["non_filer_total"] - result["filer_total"]


def test_vehicle_token_is_a_fixed_amount_for_the_cc_band():
    result = compare("TY2026", [{"type": "vehicle_token", "amount": 0, "engine_cc": 1000}])
    assert result["rows"][0]["filer_tax"] == 800
    assert result["rows"][0]["non_filer_tax"] == 1_600
    above = compare("TY2026", [{"type": "vehicle_token", "amount": 0, "engine_cc": 1001}])
    assert above["rows"][0]["filer_tax"] == 1_500
