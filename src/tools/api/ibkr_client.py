import os
import json
import requests
import pandas as pd
from pprint import pprint
from ibind import IbkrClient
from utils.timeutils import calculate_bar_period
from utils.timeutils import convert_datetimes
from utils.debugvariable import debug_variable_type

import logging
logger = logging.getLogger(__name__)

# Initialize logging for ibind
# ibind_logs_initialize()

from data.models import (
    CompanyNews,
    Price,
    PriceResponse,
    Portfolio,
    LineItem,
    InsiderTrade,
)

# Assume FinancialMetricsResponse and FinancialMetrics are defined (e.g., via Pydantic)

#ibkr_api = os.environ.get("BASE_API_URL")
#ibkr_acc = os.environ.get("ACCOUNT_ID")
#logging.debug("Using IBKR API url data: %s", ibkr_api, exc_info=True)
#logging.debug("Using IBKR Account ID : %s", ibkr_acc, exc_info=True)

#logging.debug("Startdate: %s", start_date, exc_info=True)
#logging.debug("Enddate  : %s", end_date, exc_info=True)

# Example 2: Get stock information for symbol 'AXP' (JSON response)

class IBKRClientWrapper:
    def __init__(self, cacert_path=None):
        if cacert_path is None:
            # Use an environment variable or a default path
            cacert_path = os.getenv('IBIND_CACERT', '/home/glenn/repos/ai-hedge-fund/ibeam/inputs/cacert.pem')
        self.client = IbkrClient(cacert=cacert_path)

    def check_health(self):
        return self.client.check_health()

    def tickle(self):
        return self.client.tickle().data

    def portfolio_accounts(self):
        accounts = self.client.portfolio_accounts().data
        if accounts:
            self.client.account_id = accounts[0]['accountId']
        return accounts

    def positions(self):
        return self.client.positions().data

    # Update the get_price_data function to use the new functions
    def get_price_data(self, ticker, start_date: str, end_date: str) -> pd.DataFrame:
        prices = self.get_prices(ticker, start_date, end_date)
        return self.prices_to_df(prices)

    def get_prices(self,ticker, start_date: str, end_date: str, max_retries=5):
        period=calculate_bar_period(start_date,end_date)
        md_result_dict = self.client.marketdata_history_by_symbols(ticker, period, '1d', True)
        #debug_variable_type(md_result_dict,'md_result_dict')
        # map this on original format

        # Convert all datetime / time objects in the dict
        converted_data = convert_datetimes(md_result_dict)
        transformed_data = self.transform_api_data(converted_data)
        #print(json.dumps(transformed_data, indent=2))

        # This IBKR function doesn't create a response object so it makes it hard to work with the existing code
        # Create a Response object
        response = requests.Response()

        # Set the content to a JSON string (as bytes)
        response._content = json.dumps(transformed_data).encode('utf-8')

        # Optionally, set other attributes such as status code, headers, etc.
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        response.encoding = 'utf-8'

        # Parse response with Pydantic model
        price_response = PriceResponse(**response.json())
        prices = price_response.prices

        #logging.debug("Prices (pd) : %s", prices, exc_info=True)

        if not prices:
            return []

        # json_representation = json.dumps(transformed_data, indent=2)
        # Write the raw prices response to a file
        #with open("/home/glenn/repos/ai-hedge-fund/output/get_prices_ibkr_transformed.json", "w", encoding="utf-8") as f:
        #    f.write(json_representation)

        return prices

    def get_portfolio(self):
        # pull and set account
        accounts = self.client.portfolio_accounts().data

        # get account and set on client
        self.client.account_id = accounts[0]['accountId']

        # get cache from ledger in USD
        ledger = self.client.get_ledger().data

        jsonl = json.dumps(ledger).encode('utf-8')

        #logging.debug("Ledger JSON : %s", jsonl, exc_info=True)
        #logging.debug("Ledger : %s", ledger, exc_info=True)

        total_cash = 0
        net_liq = 0

        for currency, subledger in ledger.items():
            # need to map on this strange structure:
            # class Position(BaseModel):
                # cash: float = 0.0
                # shares: int = 0
                # ticker: str
            # class Portfolio(BaseModel):
                # positions: dict[str, Position]  # ticker -> Position mapping
                # total_cash: float = 0.0
            if currency == 'BASE':
               total_cash= subledger['cashbalance']
               net_liq =subledger['stockmarketvalue']

        positions= self.client.positions().data

        #logging.debug("Port : %s", positions, exc_info=True)
        #logging.debug("Port  type: %s", type(positions), exc_info=True)

        # Define the keys you want to keep
        keys_to_keep = ['contractDesc', 'position', 'mktValue']

        # Define a mapping for renaming keys. You can add as many key mappings as needed.
        rename_map = {
            #'conid': 'ibkr_conid',
            'contractDesc': 'ticker',
            'position': 'shares',
            'mktValue': 'cash'
            # Add more renames if needed, e.g. 'conid': 'shares', etc.
        }

        # Build a new list of dictionaries with only the desired keys,
        # and rename keys according to rename_map.
        filtered_positions = [
            { rename_map.get(key, key): pos[key] for key in keys_to_keep if key in pos }
            for pos in positions
        ]

        #logging.debug("Port : %s", filtered_positions, exc_info=True)
        #logging.debug("Port  type: %s", type(filtered_positions), exc_info=True)

        #logging.debug("Port 1a: %s", filtered_positions, exc_info=True)
        #logging.debug("Port 1a type: %s", type(filtered_positions), exc_info=True)

        # Convert the list to a dict using 'ticker' as the key.
        positions_dict = { pos['ticker']: pos for pos in filtered_positions }

        # Assume positions is a list of dictionaries
        portfolio = {
            "total_cash": total_cash,
            "positions": positions_dict,
            "realized_gains": {},  # Track realized gains/losses per ticker
            "cost_basis": {},  # Track cost basis per ticker
        }

        #portfolio['positions']=positions_dict

        #logging.debug("Port 1: %s", portfolio, exc_info=True)
        #logging.debug("Port 1 type: %s", type(portfolio), exc_info=True)

        # This combined IBKR function doesn't depend on Reponse object of the 2 called ones
        # Create a Response object
        response = requests.Response()

        # Set the content to a JSON string (as bytes)
        response._content = json.dumps(portfolio).encode('utf-8')

        # Optionally, set other attributes such as status code, headers, etc.
        response.status_code = 200
        response.headers['Content-Type'] = 'application/json'
        response.encoding = 'utf-8'

        data = response.json()
        # Convert positions list to a dict keyed by ticker
        #if "positions" in data and isinstance(data["positions"], list):
            #data["positions"] = { pos["ticker"]: pos for pos in data["positions"] }
        #logging.debug("Port 2: %s", data, exc_info=True)
        #logging.debug("Port 2 type: %s", type(data), exc_info=True)

        #portfolio_response = Portfolio(**data)
        portfolio_response = Portfolio(**data)

        # Parse response with Pydantic model
        #if isinstance(data, list) and data:
        #    portfolio_response = Portfolio(**data[0])
        #else:
        #    raise ValueError("Expected a non-empty list from API.")

        #portfolio_response = Portfolio(**response.json())

        #logging.debug("Porto (pd) : %s", portfolio_response, exc_info=True)
        #logging.debug("Porto (pd) : %s", type(portfolio_response), exc_info=True)

        if not portfolio_response:
            return []

        return portfolio_response

    def get_ledger(self):
        return self.client.get_ledger().data

    def prices_to_df2(self, prices: list[Price]) -> pd.DataFrame:
        pprint(Price)
        logging.debug("Price : %s", Price, exc_info=True)
        """Convert prices to a DataFrame."""
        df = pd.DataFrame([p.model_dump() for p in prices])
        df["date"] = pd.to_datetime(df["time"])
        df.set_index("date", inplace=True)
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.sort_index(inplace=True)
        logging.debug("df  : %s", df, exc_info=True)
        return df


    def portfolio_to_df(self, positions_input) -> pd.DataFrame:
        """Convert portfolio to a DataFrame.

        The input can be:
          - A list of position dicts or Pydantic models.
          - A tuple of the form ('positions', {ticker: Position, ...}).
          - A dict with a key 'positions' mapping to a dict of positions.

        Returns:
            A DataFrame with a Date index and numeric columns.
        """
        # Normalize the input so that we end up with a list of positions.
        if isinstance(positions_input, tuple):
            # For a tuple like ('positions', { ... })
            if len(positions_input) == 2 and positions_input[0] == 'positions' and isinstance(positions_input[1], dict):
                positions_list = list(positions_input[1].values())
            else:
                positions_list = list(positions_input)
        elif isinstance(positions_input, dict):
            if 'positions' in positions_input:
                # If positions_input is like {'positions': {ticker: Position, ...}, ...}
                if isinstance(positions_input['positions'], dict):
                    positions_list = list(positions_input['positions'].values())
                else:
                    positions_list = positions_input['positions']
            else:
                # Treat the dict as a single position
                positions_list = [positions_input]
        elif isinstance(positions_input, list):
            positions_list = positions_input
        else:
            positions_list = positions_input
            #raise TypeError(f"Unrecognized positions_input type: {type(positions_input)}")

        # Now process each position in positions_list
        processed_positions = []
        for p in positions_list:
            if hasattr(p, "model_dump"):
                processed_positions.append(p.model_dump())
            elif isinstance(p, dict):
                processed_positions.append(p)
            elif isinstance(p, str):
                # If it's a JSON string, try to parse it.
                import json
                try:
                    processed_positions.append(json.loads(p))
                except Exception as e:
                    debug_variable_type(p, 'p')
                    raise ValueError(f"Unable to parse string: {p}") from e
            else:
                debug_variable_type(p, 'p')
                processed_positions.append(p)
                #raise TypeError(f"Unrecognized format: {p}")

        # At this point, processed_positions is a list of dictionaries
        # Ensure that there is a 'time' key (or adjust if your field is named differently)
        # If your positions don't have a 'time' field, you may need to change that column name.
        df = pd.DataFrame(processed_positions)

        # Convert 'time' to datetime if present
        if "time" in df.columns:
            df["Date"] = pd.to_datetime(df["time"])
            df.set_index("Date", inplace=True)

        # Convert numeric columns
        numeric_cols = ["cash", "position"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df.sort_index(inplace=True)
        return df


    def portfolio_to_df2(self, positions: list) -> pd.DataFrame:
        """Convert portfolio to a DataFrame."""
        # Convert each element appropriately:
        processed_positions = []
        for p in positions:
            if hasattr(p, "model_dump"):
                processed_positions.append(p.model_dump())
            elif isinstance(p, dict):
                processed_positions.append(p)
            elif isinstance(p, str):
                # If it's a JSON string, try to parse it.
                import json
                try:
                    processed_positions.append(json.loads(p))
                except Exception as e:
                    debug_variable_type(p,'{p}')
                    raise ValueError(f"Unable to parse string: {p}") from e
            else:
                debug_variable_type(p,p)
                logging.debug("p: %s", p, exc_info=True)
                raise TypeError(f"Unrecognized format: {p}")

        df = pd.DataFrame(processed_positions)
        df["Date"] = pd.to_datetime(df["time"])
        df.set_index("Date", inplace=True)
        numeric_cols = ["mktValue", "position"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.sort_index(inplace=True)
        return df

    def prices_to_df(self, prices: list) -> pd.DataFrame:
        """Convert prices to a DataFrame."""
        # Convert each element appropriately:
        processed_prices = []
        for p in prices:
            if hasattr(p, "model_dump"):
                processed_prices.append(p.model_dump())
            elif isinstance(p, dict):
                processed_prices.append(p)
            elif isinstance(p, str):
                # If it's a JSON string, try to parse it.
                import json
                try:
                    processed_prices.append(json.loads(p))
                except Exception as e:
                    debug_variable_type(p,'{p}')
                    raise ValueError(f"Unable to parse price string: {p}") from e
            else:
                debug_variable_type(p,'{p}')
                raise TypeError(f"Unrecognized price format: {p}")

        df = pd.DataFrame(processed_prices)
        df["Date"] = pd.to_datetime(df["time"])
        df.set_index("Date", inplace=True)
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.sort_index(inplace=True)
        return df

    #@redis_cache(expire=86400)  # caches the result for 1 day
    def get_first_us_conid(self, ticker_data):
        for entry in ticker_data:
            if entry.get('assetClass') == 'STK':
                for contract in entry.get('contracts', []):
                    if contract.get('isUS'):  # True for US exchanges (e.g., NASDAQ, NYSE, etc.)
                        return contract.get('conid')
        return None

    def transform_api_data(self, input_data: dict) -> dict:
        """
        Transforms IBKR API data for get_prices call to the format of financials:

          {
            "NVDA": [
              {
                "open": 126.17,
                "high": 127.67,
                "low": 121.8,
                "close": 123.35,
                "volume": 2619500.97,
                "date": "20240926-10:00:00"
              },
              ...
            ]
          }

        into:

          {
            "ticker": "NVDA",
            "prices": [
              {
                "ticker": "NVDA",
                "open": 126.17,
                "high": 127.67,
                "low": 121.8,
                "close": 123.35,
                "volume": 2619500.97,
                "time": "20240926-10:00:00"
              },
              ...
            ]
          }

        Args:
            input_data (dict): The raw API data.

        Returns:
            dict: The transformed data.
        """
        if not input_data:
            raise ValueError("Input data is empty.")

        # Get the first (and assumed only) key from the input, e.g. "NVDA"
        ticker = next(iter(input_data))
        raw_prices = input_data[ticker]

        new_prices = []
        for record in raw_prices:
            new_record = record.copy()
            # Insert the ticker into the record
            new_record["ticker"] = ticker
            # Rename 'date' to 'time'
            if "date" in new_record:
                new_record["time"] = new_record.pop("date")
            new_prices.append(new_record)

        # Build the final output dictionary
        transformed = {
            "ticker": ticker,
            "prices": new_prices
        }
        return transformed

    # For compatibility, if callers try to get financial metrics,
    # signal that IBKR does not support that call.
    def get_financial_metrics(self, ticker, end_date, period="ttm", limit=10):
        raise NotImplementedError("IBKR client does not implement get_financial_metrics")

    def get_market_cap( self, ticker, end_date: str, ) -> float | None:
        raise NotImplementedError("IBKR client does not implement get_market_cap")

    def prices_to_df_alt(self, prices: list) -> pd.DataFrame:
        raise NotImplementedError("IBKR client does not implement prices_to_df_alt")

    # signal that IBKR does not support that call.
    def get_insider_trades(self, ticker, end_date: str, start_date: str | None = None, limit: int = 1000, ) -> list[InsiderTrade]:
        raise NotImplementedError("IBKR client does not implement get_insider_trades")

    def get_company_news( self, ticker, end_date: str, start_date: str | None = None, limit: int = 1000, ) -> list[CompanyNews]:
        raise NotImplementedError("IBKR client does not implement get_company_news")

    def search_line_items(self, ticker, line_items: list[str], end_date: str, period: str = "30d" , limit: int = 100) -> list[LineItem]:
        raise NotImplementedError("IBKR client does not implement search_line_items")

