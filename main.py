"""
FastAPI application entry-point for the Backtesting Dashboard API.
Provides endpoints for fetching historical prices and running backtests.
"""

from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backtester import run_backtest
from models import BacktestRequest, BacktestResponse, PricePoint
from price_fetcher import fetch_prices, prices_to_response

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Backtesting Dashboard API",
    description=(
        "Options selling backtest engine using historical market data. "
        "Simulates weekly PE/CE sell entries with configurable strike offset "
        "and expiry, including rolling and expiry P&L calculations."
    ),
    version="1.0.0",
)

# Allow the Vite dev server (default port 5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/prices", response_model=List[PricePoint])
def get_prices(
    symbol: str = Query(..., description="Ticker symbol, e.g. GLD, SPY"),
    from_date: date = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., alias="to", description="End date (YYYY-MM-DD)"),
):
    """
    Return historical daily closing prices for the given symbol and date range.
    Uses yfinance under the hood.
    """
    if from_date >= to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date must be before to_date",
        )

    try:
        prices = fetch_prices(symbol, from_date, to_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return prices_to_response(prices)


@app.post("/api/backtest", response_model=BacktestResponse)
def post_backtest(req: BacktestRequest):
    """
    Run a full backtest simulation.

    Fetches prices for the requested symbol/date range, then simulates
    weekly PE/CE sell entries, daily roll checks, and expiry closures.
    Returns a row-per-trading-day results table plus total P&L.
    """
    if req.from_date >= req.to_date:
        raise HTTPException(
            status_code=400,
            detail="from_date must be before to_date",
        )

    try:
        prices = fetch_prices(req.symbol, req.from_date, req.to_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    rows, total_pnl = run_backtest(
        prices,
        expiry_months=req.expiry_months,
        strike_offset=req.strike_offset,
    )

    return BacktestResponse(
        symbol=req.symbol,
        from_date=req.from_date,
        to_date=req.to_date,
        expiry_months=req.expiry_months,
        strike_offset=req.strike_offset,
        total_pnl=total_pnl,
        rows=rows,
    )


@app.get("/health")
def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
