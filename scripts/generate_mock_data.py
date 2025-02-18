import csv
import random
from datetime import datetime, timedelta

# Parameters
num_traders = 500
num_days = 30
num_records = num_traders * random.randint(3, 20)  # Each trader trades multiple times

# Generate trader names
trader_names = [f"Trader_{i}" for i in range(1, num_traders + 1)]

# Generate random trade data
trades = []
start_date = datetime.today() - timedelta(days=num_days)
business_days = [start_date + timedelta(days=i) for i in range(num_days + 1) if (start_date + timedelta(days=i)).weekday() < 5]

for _ in range(num_records):
    trader = random.choice(trader_names)
    trade_volume = random.randint(1_000_000, 50_000_000)  # Volume in the millions
    trade_date = random.choice(business_days)
    
    trades.append([trader, trade_volume, trade_date.strftime("%Y-%m-%d")])

# Write to CSV
csv_filename = "mock_trading_data.csv"
with open(csv_filename, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["trader_name", "traded_volume", "trade_date"])  # Header
    writer.writerows(trades)

print(f"Mock trading data generated: {csv_filename}")