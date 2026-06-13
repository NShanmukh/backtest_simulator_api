"""
Wrapper around yfinance for fetching historical daily closing prices.
Provides a clean interface that returns a date-indexed pandas Series.
"""

from datetime import date
from typing import List

import pandas as pd
import yfinance as yf

from models import PricePoint


def fetch_prices(symbol: str, from_date: date, to_date: date) -> pd.Series:
    """
    Download daily closing prices for *symbol* between *from_date* and *to_date*.
    Returns a pandas Series indexed by date (datetime.date) with float close prices.
    yfinance's `end` parameter is exclusive, so we add one day to include to_date.
    """
    # yfinance end date is exclusive — shift by one day so the user's to_date is included
    end_adjusted = pd.Timestamp(to_date) + pd.Timedelta(days=1)

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=str(from_date), end=str(end_adjusted.date()))

    if df.empty:
        raise ValueError(
            f"No price data returned for symbol '{symbol}' "
            f"between {from_date} and {to_date}. "
            "Check that the symbol is valid and the date range contains trading days."
        )

    # Normalise index to plain dates (remove timezone info from yfinance timestamps)
    close_series = df["Close"]
    close_series.index = close_series.index.date
    return close_series


def prices_to_response(prices: pd.Series) -> List[PricePoint]:
    """Convert the prices Series into a list of PricePoint response objects."""
    return [
        PricePoint(date=d, close_price=round(float(p), 4))
        for d, p in prices.items()
    ]
