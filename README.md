# Options Backtesting Dashboard

A full-stack application for backtesting an options selling strategy (PE/CE) on any index or ETF using historical market data.

## Features

- **Historical price data** via `yfinance` (GLD, SPY, GC=F, etc.)
- **Weekly PE/CE sell entries** with configurable strike offset and expiry months
- **Rolling logic** — positions are rolled when the market moves through the strike
- **Expiry & P&L tracking** — intrinsic-value based P&L at position close
- **Interactive dashboard** with Ant Design table, line/area charts, and CSV export
- **Summary statistics** — total P&L, win/loss counts, trade counts

## Tech Stack

| Layer    | Technology                               |
|----------|------------------------------------------|
| Backend  | Python · FastAPI · yfinance · pandas     |
| Frontend | React · TypeScript · Vite · Ant Design · Recharts |

## Project Structure

```
backtesting-dashboard/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── backtester.py         # Core backtesting engine
│   ├── models.py             # Pydantic request/response models
│   ├── price_fetcher.py      # yfinance wrapper
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Root component
│   │   ├── components/
│   │   │   ├── FilterBar.tsx   # Input controls & Run button
│   │   │   ├── ResultsTable.tsx# Per-day results table + CSV export
│   │   │   ├── PnLSummary.tsx  # Summary statistics card
│   │   │   └── Charts.tsx      # Price & cumulative P&L charts
│   │   ├── api/
│   │   │   └── backtest.ts   # API client for backend
│   │   └── types.ts          # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 20+
- npm 9+

### Clone the Repository

```bash
git clone https://github.com/Cognition-Partner-Workshops-mirror/backtesting-dashboard.git
cd backtesting-dashboard
```

### Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dashboard will open at `http://localhost:5173`. API calls are proxied to `http://localhost:8000` via Vite's dev server proxy.

## API Endpoints

### `GET /api/prices`

Fetch historical daily closing prices.

| Parameter | Type   | Description                |
|-----------|--------|----------------------------|
| `symbol`  | string | Ticker (e.g. GLD, SPY)     |
| `from`    | date   | Start date (YYYY-MM-DD)    |
| `to`      | date   | End date (YYYY-MM-DD)      |

### `POST /api/backtest`

Run a full backtest simulation.

```json
{
  "symbol": "GLD",
  "from_date": "2024-01-01",
  "to_date": "2025-01-01",
  "expiry_months": 3,
  "strike_offset": 5
}
```

Returns a row-per-trading-day results table with position details and P&L.

## Notes

- P&L uses **intrinsic value** (strike vs. market price) since free options premium data is not available. For realistic premium-based P&L, a paid options data provider would be needed.
- `yfinance` supports many symbols: GLD (Gold ETF), GC=F (Gold Futures), SPY (S&P 500), QQQ (Nasdaq 100), etc.
- The strike offset should be adjusted based on the price level of the chosen symbol (e.g. 5 for GLD ≈ $190, but much larger for SPY ≈ $450).
