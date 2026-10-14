"""Pure tax arithmetic. Every rate comes from the JSON rules for that tax year."""

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parent / "tax_rules"
YEARS = ("TY2026", "TY2027")
REGIMES = ("pseb_export", "export_services", "local_services")
FILER_STATUSES = ("filer", "late_filer", "non_filer")
PRIOR = {"TY2027": "TY2026"}
_NEED_KIND = "Say salary, freelancer receipts, or a property purchase or sale, plus the rupees."

_AMOUNT = re.compile(r"\d[\d,]*")
_CC = re.compile(r"(\d[\d,]*)\s*cc\b", re.IGNORECASE)


class TaxError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@lru_cache(maxsize=4)
def load_rules(tax_year: str) -> dict:
    if tax_year not in YEARS:
        raise TaxError("invalid_tax_year", "tax_year must be TY2026 or TY2027.")
    path = RULES_DIR / f"{tax_year.lower()}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def salary(tax_year: str, annual_income: int) -> dict:
    rules = load_rules(tax_year)
    income = _money(annual_income, "annual_income")
    slab_tax, line = _salary_line(rules, income)
    lines = [line]
    total = slab_tax
    surcharge = rules["surcharge"]["salaried"]
    rate = _dec(surcharge["rate_on_tax"])
    if income > int(surcharge["income_above"]) and rate > 0:
        extra = _rupees(rate * Decimal(slab_tax))
        lines.append(
            {
                "label": "Section 4AB surcharge",
                "base": slab_tax,
                "rate": _num(rate),
                "tax": extra,
                "source": rules["surcharge"]["source"],
            }
        )
        total += extra
    return _envelope(
        rules,
        {"annual_income": income},
        total,
        income,
        lines,
        _salary_notes(rules, income),
        monthly=True,
    )


def freelancer(
    tax_year: str, annual_receipts: int, regime: str, filer_status: str = "filer"
) -> dict:
    rules = load_rules(tax_year)
    receipts = _money(annual_receipts, "annual_receipts")
    if regime not in rules["freelancer"]:
        raise TaxError("invalid_request", "Unknown freelancer regime.")
    status = _status(filer_status)
    entry = rules["freelancer"][regime]
    if status == "late_filer" or status not in entry:
        raise TaxError("invalid_request", "Late filer does not apply to freelancer rates.")
    rate = _dec(entry[status])
    tax = _rupees(rate * Decimal(receipts))
    names = {
        "pseb_export": "PSEB-registered export of IT services",
        "export_services": "Export of services, not PSEB-registered",
        "local_services": "Domestic IT and IT enabled services",
    }
    line = {
        "label": names[regime],
        "base": receipts,
        "rate": _num(rate),
        "tax": tax,
        "source": entry["source"],
    }
    notes = [
        f"Regime used: {regime}.",
        "This is the federal rate on gross receipts under the cited section, not a full return.",
    ]
    return _envelope(
        rules,
        {"annual_receipts": receipts, "regime": regime, "filer_status": status},
        tax,
        receipts,
        [line],
        notes,
        monthly=True,
    )


def property_tax(
    tax_year: str,
    side: str,
    value: int,
    filer_status: str,
    holding_period_years: int | None = None,
) -> dict:
    rules = load_rules(tax_year)
    if side not in ("purchase", "sale"):
        raise TaxError("invalid_request", "side must be purchase or sale.")
    amount = _money(value, "value")
    key = "property_purchase" if side == "purchase" else "property_sale"
    row = _withholding_row(rules, key, amount, filer_status, None)
    notes = [
        "Federal withholding only. Provincial stamp duty and fees are not included.",
        "The federal rate on this card does not change with holding period.",
    ]
    inputs = {"side": side, "value": amount, "filer_status": filer_status}
    if holding_period_years is not None:
        inputs["holding_period_years"] = holding_period_years
    return _envelope(rules, inputs, row["tax"], amount, [row["line"]], notes)


def compare(tax_year: str, transactions: list[dict]) -> dict:
    rules = load_rules(tax_year)
    if not transactions:
        raise TaxError("invalid_request", "At least one transaction is required.")
    valid = sorted(rules["withholding"])
    rows = []
    filer_total = 0
    non_filer_total = 0
    for item in transactions:
        kind = str(item.get("type") or "")
        if kind not in rules["withholding"]:
            raise TaxError(
                "unknown_transaction_type",
                "That transaction type is not in this year's rules.",
                {"valid": valid},
            )
        amount = _money(item.get("amount", 0), "amount")
        engine_cc = item.get("engine_cc")
        entry = rules["withholding"][kind]
        if "by_engine_cc" in entry and engine_cc is None:
            raise TaxError("invalid_request", f"{kind} needs engine_cc.")
        filer = _one_status(entry, amount, engine_cc, "filer")
        non_filer = _one_status(entry, amount, engine_cc, "non_filer")
        late = (
            _one_status(entry, amount, engine_cc, "late_filer")
            if _has_status(entry, "late_filer")
            else None
        )
        rows.append(
            {
                "type": kind,
                "amount": amount,
                "engine_cc": engine_cc,
                "filer_tax": filer,
                "late_filer_tax": late,
                "non_filer_tax": non_filer,
                "difference": non_filer - filer,
                "source": entry["source"],
            }
        )
        filer_total += filer
        non_filer_total += non_filer
    return {
        "tax_year": tax_year,
        "rows": rows,
        "filer_total": filer_total,
        "non_filer_total": non_filer_total,
        "savings": non_filer_total - filer_total,
        "notes": ["A blank late-filer cell means this year has no separate rate."],
        "rules_version": rules["rules_version"],
    }


def chat_tool(
    intent: str, message: str, tax_year: str, params: dict | None = None
) -> tuple[str | None, dict | None, str]:
    """Return card type, card data, and a short answer. Type is None if a number is missing."""
    params = params or {}
    year = params.get("tax_year") if params.get("tax_year") in YEARS else tax_year
    if year not in YEARS:
        year = "TY2027"
    text = message.lower()
    try:
        if intent == "compare_filer":
            return _chat_compare(year, text, message, params)
        return _chat_calculate(year, text, message, params)
    except TaxError as exc:
        return None, None, exc.message


def _chat_calculate(
    year: str, text: str, message: str, params: dict
) -> tuple[str | None, dict | None, str]:
    amount = _amount(message, params)
    if _is_property(text):
        if amount is None:
            return None, None, "Tell me the property value in rupees."
        side = "sale" if any(word in text for word in ("sale", "sold", "sell")) else "purchase"
        result = property_tax(year, side, amount, _filer(text))
        return "calculation", result, _sentence(result, "Federal withholding")
    if _is_freelancer(text):
        if amount is None:
            return None, None, "Tell me the annual receipts in rupees."
        regime = _regime(text)
        result = freelancer(year, amount, regime, _filer(text))
        return "calculation", result, _sentence(result, "Federal tax on those receipts")
    if _is_salary(text) or amount is not None:
        if amount is None:
            return None, None, "Tell me the annual salary in rupees."
        if not _is_salary(text) and not _is_freelancer(text) and not _is_property(text):
            if not any(word in text for word in ("salary", "salaried", "income", "tax")):
                return None, None, _NEED_KIND
        result = salary(year, amount)
        return "calculation", result, _sentence(result, "Federal salary tax")
    return None, None, _NEED_KIND


def _chat_compare(
    year: str, text: str, message: str, params: dict
) -> tuple[str | None, dict | None, str]:
    amount = _amount(message, params)
    kind = _compare_kind(text)
    if kind is None:
        return None, None, "Say property, vehicle, dividend, or profit on debt."
    if amount is None and kind != "vehicle_token":
        return None, None, "Tell me the amount in rupees."
    item: dict = {"type": kind, "amount": amount or 0}
    if kind.startswith("vehicle"):
        cc = _engine_cc(message)
        if cc is None:
            return None, None, "Tell me the engine capacity in cc."
        item["engine_cc"] = cc
    result = compare(year, [item])
    row = result["rows"][0]
    answer = (
        f"On Rs {row['amount']:,}, a filer pays Rs {row['filer_tax']:,} and a non-filer pays "
        f"Rs {row['non_filer_tax']:,}. The difference is Rs {row['difference']:,}."
    )
    return "filer_comparison", result, answer


def _sentence(result: dict, label: str) -> str:
    total = result["total_tax"]
    text = f"{label} for {result['tax_year']} is Rs {total:,} a year."
    if "monthly_tax" in result:
        text += f" That is about Rs {result['monthly_tax']:,} a month."
    change = result.get("compared_to")
    if change:
        gap = change["difference"]
        direction = "higher" if gap > 0 else "lower" if gap < 0 else "the same"
        text += f" Compared with {change['tax_year']}, this is Rs {abs(gap):,} {direction}."
    return text


def _salary_line(rules: dict, income: int) -> tuple[int, dict]:
    slab = _salary_slab(rules["salary"]["slabs"], income)
    rate = _dec(slab["rate"])
    base = income - int(slab["from"])
    tax = _rupees(Decimal(int(slab["fixed"])) + rate * Decimal(base))
    end = "and above" if slab["to"] is None else f"to {int(slab['to']):,}"
    return tax, {
        "label": f"Slab: {int(slab['from']):,} {end}",
        "base": base,
        "rate": _num(rate),
        "tax": tax,
        "source": rules["salary"]["source"],
    }


def _salary_slab(slabs: list[dict], income: int) -> dict:
    for slab in slabs:
        if slab["to"] is None or income <= int(slab["to"]):
            return slab
    return slabs[-1]


def _withholding_row(
    rules: dict, key: str, amount: int, status: str, engine_cc: int | None
) -> dict:
    status = _status(status)
    entry = rules["withholding"][key]
    if not _has_status(entry, status):
        raise TaxError("invalid_request", "This year has no late-filer rate for that section.")
    tax = _one_status(entry, amount, engine_cc, status)
    rate = _status_rate(entry, amount, engine_cc, status)
    return {
        "tax": tax,
        "line": {
            "label": key.replace("_", " "),
            "base": amount,
            "rate": None if rate is None else _num(rate),
            "tax": tax,
            "source": entry["source"],
        },
    }


def _one_status(entry: dict, amount: int, engine_cc: int | None, status: str) -> int:
    if "by_engine_cc" in entry:
        band = _capped(entry["by_engine_cc"], int(engine_cc), "max_cc")
        if entry.get("basis") == "fixed":
            return int(band[status])
        return _rupees(_dec(band[status]) * Decimal(amount))
    if "bands" in entry:
        band = _capped(entry["bands"], amount, "to")
        return _rupees(_dec(band[status]) * Decimal(amount))
    return _rupees(_dec(entry[status]) * Decimal(amount))


def _status_rate(entry: dict, amount: int, engine_cc: int | None, status: str) -> Decimal | None:
    if entry.get("basis") == "fixed":
        return None
    if "by_engine_cc" in entry:
        return _dec(_capped(entry["by_engine_cc"], int(engine_cc), "max_cc")[status])
    if "bands" in entry:
        return _dec(_capped(entry["bands"], amount, "to")[status])
    return _dec(entry[status])


def _has_status(entry: dict, status: str) -> bool:
    if "by_engine_cc" in entry:
        return status in entry["by_engine_cc"][0]
    if "bands" in entry:
        return status in entry["bands"][0]
    return status in entry


def _capped(bands: list[dict], value: int, key: str) -> dict:
    for band in bands:
        cap = band[key]
        if cap is None or value <= int(cap):
            return band
    return bands[-1]


def _envelope(rules, inputs, total, base, lines, notes, monthly: bool = False) -> dict:
    body = {
        "tax_year": rules["tax_year"],
        "inputs": inputs,
        "total_tax": total,
        "effective_rate": 0.0 if base == 0 else _num(Decimal(total) / Decimal(base)),
        "breakdown": lines,
        "notes": notes + _change_note(rules, inputs, total),
        "rules_version": rules["rules_version"],
        "compared_to": _compared(rules, inputs, total),
    }
    if monthly:
        body["monthly_tax"] = _rupees(Decimal(total) / Decimal(12))
        net = base - total
        body["net_annual"] = net
        body["net_monthly"] = _rupees(Decimal(net) / Decimal(12))
    return body


def _compared(rules: dict, inputs: dict, total: int) -> dict | None:
    prior = PRIOR.get(rules["tax_year"])
    if prior is None:
        return None
    other = _same(prior, inputs)
    return {"tax_year": prior, "total_tax": other, "difference": total - other}


def _change_note(rules: dict, inputs: dict, total: int) -> list[str]:
    change = _compared(rules, inputs, total)
    if change is None:
        return []
    gap = change["difference"]
    if gap == 0:
        return [f"Same federal amount as {change['tax_year']}."]
    word = "more" if gap > 0 else "less"
    return [f"Rs {abs(gap):,} {word} than {change['tax_year']}."]


def _same(tax_year: str, inputs: dict) -> int:
    if "annual_income" in inputs:
        return salary(tax_year, inputs["annual_income"])["total_tax"]
    if "annual_receipts" in inputs:
        return freelancer(
            tax_year, inputs["annual_receipts"], inputs["regime"], inputs["filer_status"]
        )["total_tax"]
    return property_tax(
        tax_year,
        inputs["side"],
        inputs["value"],
        inputs["filer_status"],
        inputs.get("holding_period_years"),
    )["total_tax"]


def _salary_notes(rules: dict, income: int) -> list[str]:
    rate = _dec(rules["surcharge"]["salaried"]["rate_on_tax"])
    if rate == 0:
        return ["Section 4AB does not add a surcharge on salary for this tax year."]
    if income > int(rules["surcharge"]["salaried"]["income_above"]):
        return ["Section 4AB adds a surcharge because salary income exceeds Rs 10,000,000."]
    return ["Section 4AB surcharge applies only when taxable salary income exceeds Rs 10,000,000."]


def _money(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TaxError("invalid_request", f"{name} must be a whole number of rupees, zero or more.")
    return value


def _status(value: str) -> str:
    if value not in FILER_STATUSES:
        raise TaxError("invalid_request", "filer_status must be filer, late_filer, or non_filer.")
    return value


def _dec(value) -> Decimal:
    return Decimal(str(value))


def _rupees(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _num(amount: Decimal) -> float:
    return float(amount.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _amount(message: str, params: dict) -> int | None:
    for key in ("annual_income", "annual_receipts", "amount", "value"):
        if isinstance(params.get(key), int):
            return params[key]
    numbers = []
    for match in _AMOUNT.finditer(message):
        raw = match.group().replace(",", "")
        if not raw.isdigit():
            continue
        if re.match(r"\s*cc\b", message[match.end() :], re.IGNORECASE):
            continue
        value = int(raw)
        if value in (2026, 2027):
            continue
        numbers.append(value)
    if not numbers:
        return None
    large = [value for value in numbers if value >= 1000]
    return max(large or numbers)


def _engine_cc(message: str) -> int | None:
    match = _CC.search(message)
    if match is None:
        return None
    return int(match.group(1).replace(",", ""))


def _filer(text: str) -> str:
    if "late" in text:
        return "late_filer"
    if "non-filer" in text or "non filer" in text or "nonfiler" in text:
        return "non_filer"
    return "filer"


def _regime(text: str) -> str:
    if "pseb" in text:
        return "pseb_export"
    if "domestic" in text or "local" in text:
        return "local_services"
    return "export_services"


def _is_property(text: str) -> bool:
    return any(word in text for word in ("property", "plot", "immovable", "236c", "236k"))


def _is_freelancer(text: str) -> bool:
    words = ("freelance", "freelancer", "upwork", "fiverr", "pseb", "export")
    return any(word in text for word in words)


def _is_salary(text: str) -> bool:
    return any(word in text for word in ("salary", "salaried", "wage"))


def _compare_kind(text: str) -> str | None:
    if "dividend" in text:
        return "dividend"
    if "profit" in text or "debt" in text:
        return "profit_on_debt"
    if "token" in text or "annual tax" in text:
        return "vehicle_token"
    if any(word in text for word in ("vehicle", "car", "motor")):
        return "vehicle_registration"
    if any(word in text for word in ("sale", "sold", "sell")):
        return "property_sale"
    if any(word in text for word in ("property", "plot", "purchase", "buy")):
        return "property_purchase"
    return None
