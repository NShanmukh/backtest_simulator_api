import requests
import json

resp = requests.post(
    'http://localhost:8000/api/backtest',
    json={
        'symbol': 'SPY',
        'from_date': '2024-01-01',
        'to_date': '2024-01-31',
        'expiry_months': 3,
        'strike_offset': 5,
        'profit_target': 0.10
    }
)

data = resp.json()
print(f"Total P&L: {data['total_pnl']}")
print("\nRows with activity:")
for r in data['rows']:
    if r['open_pes'] > 0 or r['rolled_today'] or r['closed_today']:
        print(f"{r['date']}: open_pes={r['open_pes']}, open_ces={r['open_ces']}, rolled={len(r['rolled_today'])}, closed={len(r['closed_today'])}")
        if r['rolled_today']:
            print(f"  Rolled: {r['rolled_today']}")
        if r['closed_today']:
            print(f"  Closed: {r['closed_today']}")

print("\n\nFirst 15 days:")
for r in data['rows'][:15]:
    print(f"{r['date']}: price={r['price']:.2f}, pes={r['open_pes']}, ces={r['open_ces']}, pnl={r['pnl']:.2f}")
