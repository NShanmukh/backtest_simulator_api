"""
Core backtesting engine for options selling strategy simulation.

Strategy overview:
- Every Monday (or first trading day of the week), open new PE sell and CE sell
  positions offset from the current market price.
- Daily, check if any open position should be "rolled" because the market has
  moved through the strike price.
- Positions close at their expiry date; P&L is calculated using intrinsic value
  because real premium data is unavailable from free data sources.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

import pandas as pd
from dateutil.relativedelta import relativedelta

from models import (
    BacktestRow,
    ClosedPosition,
    RolledPosition,
)


# ---------------------------------------------------------------------------
# Internal position representation
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """
    Represents a single open PE or CE sell position.
    `status` tracks whether the position is still open, was rolled, or expired.
    """

    type: str  # "PE" or "CE"
    strike: float
    entry_date: date
    expiry_date: date
    entry_price: float  # market price at the time of entry
    status: str = "open"  # open | rolled | closed


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _is_monday(current: date) -> bool:
    """Return True if *current* is a Monday."""
    return current.weekday() == 0


def _is_start_of_week(current: date, previous: Optional[date]) -> bool:
    """
    Return True if *current* is a Monday, OR if it is the first trading day
    we have seen this week (handles weeks where Monday is a holiday).
    """
    if current.weekday() == 0:
        return True
    # If there was no previous trading day, treat as week start
    if previous is None:
        return True
    # If the previous trading day was in a different ISO week, this is the
    # first trading day of the new week
    return current.isocalendar()[1] != previous.isocalendar()[1]


def _calc_pe_pnl(strike: float, market_price: float) -> float:
    """
    P&L for a PE (put) sell position at close.
    - If market >= strike → full profit (premium kept, simplified to 0 intrinsic loss)
    - If market < strike  → loss = strike - market_price
    """
    if market_price >= strike:
        return 0.0  # kept premium; no intrinsic loss
    return -(strike - market_price)  # negative P&L = loss


def _calc_ce_pnl(strike: float, market_price: float) -> float:
    """
    P&L for a CE (call) sell position at close.
    - If market <= strike → full profit
    - If market > strike  → loss = market_price - strike
    """
    if market_price <= strike:
        return 0.0
    return -(market_price - strike)


# ---------------------------------------------------------------------------
# Main backtest runner
# ---------------------------------------------------------------------------

def run_backtest(
    prices: pd.Series,
    expiry_months: int = 3,
    strike_offset: float = 5.0,
    profit_target: float = 0.10,
) -> Tuple[List[BacktestRow], float]:
    """
    Execute the backtesting simulation over the provided price series.

    Parameters
    ----------
    prices : pd.Series
        Date-indexed series of daily closing prices.
    expiry_months : int
        Months until each new position expires (default 3).
    strike_offset : float
        Distance from market price for PE/CE strikes (default 5).
    profit_target : float
        Profit target as a percentage of strike_offset (default 0.10 = 10%).
        Positions exit when profit reaches this target.

    Returns
    -------
    rows : list[BacktestRow]
        One row per trading day with full position details.
    total_pnl : float
        Cumulative P&L across the entire simulation.
    """
    positions: List[Position] = []
    rows: List[BacktestRow] = []
    total_pnl: float = 0.0
    prev_date: Optional[date] = None

    trading_days = list(prices.index)

    for day in trading_days:
        price = float(prices[day])

        day_rolled: List[RolledPosition] = []
        day_closed: List[ClosedPosition] = []
        day_pnl: float = 0.0
        new_pe_strike: Optional[float] = None
        new_ce_strike: Optional[float] = None

        # --- 1. Profit target & rolling logic: check every open position ---
        # First, close positions that hit their profit target
        for pos in positions:
            if pos.status != "open":
                continue

            # For both PE and CE sells, we profit when market stays favorable
            # PE: profitable when market < strike
            # CE: profitable when market < strike  
            # Profit target: intrinsic value = strike_offset * profit_target
            # Close when: market <= strike - (strike_offset * profit_target)
            
            if pos.type == "PE" and price <= pos.strike - (strike_offset * profit_target):
                # PE profit target hit
                pnl = _calc_pe_pnl(pos.strike, price)
                day_closed.append(
                    ClosedPosition(
                        type="PE",
                        strike=round(pos.strike, 4),
                        entry_date=pos.entry_date,
                        pnl=round(pnl, 4),
                    )
                )
                day_pnl += pnl
                pos.status = "closed"

            elif pos.type == "CE" and price <= pos.strike - (strike_offset * profit_target):
                # CE profit target hit
                pnl = _calc_ce_pnl(pos.strike, price)
                day_closed.append(
                    ClosedPosition(
                        type="CE",
                        strike=round(pos.strike, 4),
                        entry_date=pos.entry_date,
                        pnl=round(pnl, 4),
                    )
                )
                day_pnl += pnl
                pos.status = "closed"

        # Rolling logic: only on Mondays, check if positions should be rolled
        new_positions_from_rolls: List[Position] = []
        if _is_monday(day):
            for pos in positions:
                if pos.status != "open":
                    continue

                rolled = False
                if pos.type == "PE" and price < pos.strike:
                    # Market dropped below PE strike → roll the PE
                    pnl = _calc_pe_pnl(pos.strike, price)
                    day_rolled.append(
                        RolledPosition(
                            type="PE",
                            old_strike=round(pos.strike, 4),
                            new_strike=round(price - strike_offset, 4),
                            pnl=round(pnl, 4),
                        )
                    )
                    day_pnl += pnl
                    pos.status = "rolled"
                    # Open replacement PE at new strike, same expiry
                    new_positions_from_rolls.append(
                        Position(
                            type="PE",
                            strike=round(price - strike_offset, 4),
                            entry_date=day,
                            expiry_date=pos.expiry_date,
                            entry_price=price,
                        )
                    )
                    rolled = True

                if not rolled and pos.type == "CE" and price > pos.strike:
                    # Market rose above CE strike → roll the CE
                    pnl = _calc_ce_pnl(pos.strike, price)
                    day_rolled.append(
                        RolledPosition(
                            type="CE",
                            old_strike=round(pos.strike, 4),
                            new_strike=round(price + strike_offset, 4),
                            pnl=round(pnl, 4),
                        )
                    )
                    day_pnl += pnl
                    pos.status = "rolled"
                    # Open replacement CE at new strike, same expiry
                    new_positions_from_rolls.append(
                        Position(
                            type="CE",
                            strike=round(price + strike_offset, 4),
                            entry_date=day,
                            expiry_date=pos.expiry_date,
                            entry_price=price,
                        )
                    )

        # Add rolled-replacement positions to the book
        positions.extend(new_positions_from_rolls)

        # --- 2. Expiry logic: close positions whose expiry has passed ---
        for pos in positions:
            if pos.status != "open":
                continue
            if pos.expiry_date <= day:
                if pos.type == "PE":
                    pnl = _calc_pe_pnl(pos.strike, price)
                else:
                    pnl = _calc_ce_pnl(pos.strike, price)

                day_closed.append(
                    ClosedPosition(
                        type=pos.type,
                        strike=round(pos.strike, 4),
                        entry_date=pos.entry_date,
                        pnl=round(pnl, 4),
                    )
                )
                day_pnl += pnl
                pos.status = "closed"

        # --- 3. New positions on Mondays (or first trading day of the week) ---
        if _is_start_of_week(day, prev_date):
            pe_strike = round(price - strike_offset, 4)
            ce_strike = round(price + strike_offset, 4)
            expiry = day + relativedelta(months=expiry_months)

            positions.append(
                Position(
                    type="PE",
                    strike=pe_strike,
                    entry_date=day,
                    expiry_date=expiry,
                    entry_price=price,
                )
            )
            positions.append(
                Position(
                    type="CE",
                    strike=ce_strike,
                    entry_date=day,
                    expiry_date=expiry,
                    entry_price=price,
                )
            )
            new_pe_strike = pe_strike
            new_ce_strike = ce_strike

        # --- 4. Count remaining open positions ---
        open_pes = sum(
            1 for p in positions if p.status == "open" and p.type == "PE"
        )
        open_ces = sum(
            1 for p in positions if p.status == "open" and p.type == "CE"
        )

        total_pnl += day_pnl

        rows.append(
            BacktestRow(
                date=day,
                price=round(price, 4),
                new_pe=new_pe_strike,
                open_pes=open_pes,
                new_ce=new_ce_strike,
                open_ces=open_ces,
                rolled_today=day_rolled,
                closed_today=day_closed,
                pnl=round(day_pnl, 4),
            )
        )

        prev_date = day

    return rows, round(total_pnl, 4)
