"""
Pydantic models for API request/response schemas.
Defines the data contracts between frontend and backend.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Request Models ---


class BacktestRequest(BaseModel):
    """
    Request body for the POST /api/backtest endpoint.
    Contains all parameters needed to run a backtesting simulation.
    """

    symbol: str = Field(..., description="Ticker symbol (e.g. GLD, SPY, GC=F)")
    from_date: date = Field(..., description="Start date of the backtest range")
    to_date: date = Field(..., description="End date of the backtest range")
    expiry_months: int = Field(
        default=3,
        ge=1,
        le=12,
        description="Number of months until option expiry",
    )
    strike_offset: float = Field(
        default=5.0,
        gt=0,
        description="Gap between market price and PE/CE strike prices",
    )


# --- Response Models ---


class PricePoint(BaseModel):
    """Single data point of historical closing price."""

    date: date
    close_price: float


class RolledPosition(BaseModel):
    """Details of a position that was rolled on a given day."""

    type: str = Field(..., description="PE or CE")
    old_strike: float
    new_strike: float
    pnl: float = Field(..., description="P&L realised when closing the old position")


class ClosedPosition(BaseModel):
    """Details of a position that expired/closed on a given day."""

    type: str = Field(..., description="PE or CE")
    strike: float
    entry_date: date
    pnl: float


class BacktestRow(BaseModel):
    """
    One row of the backtest results table, representing a single trading day.
    Aggregates new positions, open counts, rolls, closures, and daily P&L.
    """

    date: date
    price: float
    new_pe: Optional[float] = Field(
        None, description="New PE strike opened (Monday only)"
    )
    open_pes: int = Field(..., description="Count of open PE positions as of this day")
    new_ce: Optional[float] = Field(
        None, description="New CE strike opened (Monday only)"
    )
    open_ces: int = Field(..., description="Count of open CE positions as of this day")
    rolled_today: List[RolledPosition] = Field(
        default_factory=list, description="Positions rolled on this day"
    )
    closed_today: List[ClosedPosition] = Field(
        default_factory=list, description="Positions that expired/closed today"
    )
    pnl: float = Field(
        ..., description="Total P&L from all closed/rolled positions today"
    )


class BacktestResponse(BaseModel):
    """Full response from the backtesting engine."""

    symbol: str
    from_date: date
    to_date: date
    expiry_months: int
    strike_offset: float
    total_pnl: float = Field(..., description="Sum of all P&L across the backtest")
    rows: List[BacktestRow]
