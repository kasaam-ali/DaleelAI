"""Salary, freelancer, property, and filer comparison. The arithmetic is in tax_engine."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.v1.schemas import (
    CalculationResponse,
    FilerCompareRequest,
    FilerComparisonResponse,
    FreelancerRequest,
    PropertyRequest,
    SalaryRequest,
)
from app.core.tax_engine import TaxError, compare, freelancer, property_tax, salary

router = APIRouter()


def _error(exc: TaxError) -> JSONResponse:
    body: dict = {"error": {"code": exc.code, "message": exc.message}}
    if exc.details:
        body["error"]["details"] = exc.details
    return JSONResponse(body, status_code=400)


@router.post("/calculator/salary", response_model=CalculationResponse)
def salary_tax(body: SalaryRequest) -> CalculationResponse | JSONResponse:
    monthly = body.monthly_income or 0
    annual = body.annual_income if body.annual_income is not None else monthly * 12
    try:
        return salary(body.tax_year, annual)
    except TaxError as exc:
        return _error(exc)


@router.post("/calculator/freelancer", response_model=CalculationResponse)
def freelancer_tax(body: FreelancerRequest) -> CalculationResponse | JSONResponse:
    try:
        return freelancer(body.tax_year, body.annual_receipts, body.regime, body.filer_status)
    except TaxError as exc:
        return _error(exc)


@router.post("/calculator/property", response_model=CalculationResponse)
def property_withholding(body: PropertyRequest) -> CalculationResponse | JSONResponse:
    try:
        return property_tax(
            body.tax_year,
            body.side,
            body.value,
            body.filer_status,
            body.holding_period_years,
        )
    except TaxError as exc:
        return _error(exc)


@router.post("/compare/filer", response_model=FilerComparisonResponse)
def filer_comparison(body: FilerCompareRequest) -> FilerComparisonResponse | JSONResponse:
    try:
        return compare(body.tax_year, [item.model_dump() for item in body.transactions])
    except TaxError as exc:
        return _error(exc)
