import os
import re
import time
import requests
import pandas as pd
from pprint import pprint
from utils.helpers import is_valid_url

from utils.timeutils import convert_to_date, extract_date_limits
from utils.debugvariable import debug_variable_type

from data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
)

from utils.cache import redis_cache

import logging
logger = logging.getLogger(__name__)

class AlphavantageAPIClient:
    def __init__(self, config=None):
        self.config = config or {}

        # Limit might be used to restrict to 5 tickers, etc.
        self.limit = self.config.get("limit", 5)
        self.url = self.config.get("ALPHAVANTAGE_BASE_API_URL", 5)
        self.key = self.config.get("ALPHAVANTAGE_API_KEY", 5)

        if os.environ.get("ALPHAVANTAGE_API_KEY"):
            self.key = self.config.get("ALPHAVANTAGE_API_KEY")
        else:
            self.key ="None"

        self.url ="https://www.alphavantage.co/query"
        if os.environ.get("ALPHAVANTAGE_BASE_API_URL"):
            self.url= os.environ.get("ALPHAVANTAGE_BASE_API_URL")

        # Validate the URL and raise an exception if it's not valid.
        if not is_valid_url(self.url):
            raise ValueError(f"Invalid URL: {self.url}")

    @redis_cache(expire=86400)  # caches the result for 1 day
    def get_financial_metrics(self, ticker: str, end_date: str, period: str = "ttm", limit: int = 10,) -> list[FinancialMetrics]:
#        # Check cache first
#        if cached_data := get_cache_financial_metrics(ticker):
#            filtered_data = [metric for metric in cached_data if metric["report_period"] <= end_date]
#            filtered_data.sort(key=lambda x: x["report_period"], reverse=True)
#            if filtered_data:
#                return filtered_data[:limit]
# ALPHAVANTAGE_API_KEY=NCOBND9RVKX87N9C
# ALPHAVANTAGE_BASE_API_URL=https://www.alphavantage.co

        headers = {}
        if self.key:
            headers["X-API-KEY"] = self.key

        params = {
            "ticker": ticker,
            "end_date": end_date,
            "limit": limit,
            "period": period
        }

        response = requests.get(self.url, headers=headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

        # Expecting a JSON response with a key "financial_metrics"
        data = response.json()
        financial_metrics = data.get("financial_metrics", [])
        #set_cache_financial_metrics(ticker, financial_metrics)
        return financial_metrics

    @redis_cache(expire=86400)  # caches the result for 1 day
    def get_prices(self, ticker, start_date: str, end_date: str, max_retries=5, limit=5000):
        """Fetch price data from API with retry logic for rate limiting and server errors."""
        headers = {}
        if self.key:
            headers["X-API-KEY"] = self.key

        params = {
            "ticker": ticker,
            "interval": "day",
            "interval_multiplier": 1,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit # max for API
        }

        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(self.url, params=params, headers=headers)
                # If rate-limited (HTTP 429)
                if response.status_code == 429:
                    try:
                        data = response.json()
                        detail = data.get("detail", "")
                        # Try to extract the delay from the detail message, e.g., "Expected available in 1 second"
                        match = re.search(r'(\d+)\s*second', detail)
                        delay = int(match.group(1)) if match else 1
                    except Exception:
                        delay = 1
                    logger.warning("429 received. Throttled. Retrying in %d second(s) (attempt %d/%d)",
                                   delay, retries + 1, max_retries)
                    time.sleep(delay*2)
                    retries += 1
                    continue

                # If server errors (5xx)
                if response.status_code >= 500:
                    delay = 2 ** retries  # exponential backoff
                    logger.warning("Server error %d. Retrying in %d second(s) (attempt %d/%d)",
                                   response.status_code, delay, retries + 1, max_retries)
                    time.sleep(delay*2)
                    retries += 1
                    continue

                # Parse response with Pydantic model
                price_response = PriceResponse(**response.json())
                prices = price_response.prices

                if not prices:
                    return []

                # For other non-success statuses, raise an exception
                response.raise_for_status()

                return price_response

            except requests.exceptions.RequestException as e:
                # This catches network-related errors
                delay = 2 ** retries  # exponential backoff
                logger.warning("Network error: %s. Retrying in %d second(s) (attempt %d/%d)",
                               e, delay, retries + 1, max_retries)
                time.sleep(delay*2)
                retries += 1

        raise Exception("Max retries exceeded while attempting to get prices.")

    @redis_cache(expire=86400)  # caches the result for 1 day
    def search_line_items(self, ticker, line_items: list[str], end_date: str, period: str = "30d" , limit: int = 100) -> list[LineItem]:
      """Fetch line items from API."""
      # If not in cache or insufficient data, fetch from API
      headers = {}

      if self.key:
          headers["X-API-KEY"] = self.key

      url = "https://api.financialdatasets.ai/financials/search/line-items"

      body = {
          "tickers": [ticker],
          "line_items": line_items,
          "end_date": end_date,
          "period": period,
          "limit": limit
      }

      response = requests.post(url, headers=headers, json=body)
      if response.status_code != 200:
          raise Exception(f"Error fetching data: {response.status_code} - {response.text}")
      data = response.json()
      response_model = LineItemResponse(**data)
      search_results = response_model.search_results
      if not search_results:
          return []

      return search_results[:limit]

    @redis_cache(expire=86400)  # caches the result for 1 day
    def get_insider_trades(self, ticker, end_date: str, start_date: str | None = None, limit: int = 1000, ) -> list[InsiderTrade]:
        """Fetch insider trades from cache or API."""
        # Check cache first
#        if cached_data := _cache.get_insider_trades(ticker):
#            # Filter cached data by date range
#            filtered_data = [InsiderTrade(**trade) for trade in cached_data
#                            if (start_date is None or (trade.get("transaction_date") or trade["filing_date"]) >= start_date)
#                            and (trade.get("transaction_date") or trade["filing_date"]) <= end_date]
#            filtered_data.sort(key=lambda x: x.transaction_date or x.filing_date, reverse=True)
#            if filtered_data:
#                return filtered_data

        # If not in cache or insufficient data, fetch from API
        headers = {}
        if self.key:
            headers["X-API-KEY"] = self.key

        all_trades = []
        current_end_date = end_date

        url = "https://api.financialdatasets.ai/insider-trades/"

        # Build params list
        params = {
            "ticker": ticker,
            "filing_date_lte": current_end_date,
            "limit": limit
        }
        # Only add 'filing_date_gte' if start_date is defined.
        if start_date:
            params["filing_date_gte"] = start_date

        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

            data = response.json()
            response_model = InsiderTradeResponse(**data)
            insider_trades = response_model.insider_trades

            if not insider_trades:
                break

            all_trades.extend(insider_trades)

            # Only continue pagination if we have a start_date and got a full page
            if not start_date or len(insider_trades) < limit:
                break

            # Update end_date to the oldest filing date from current batch for next iteration
            current_end_date = min(trade.filing_date for trade in insider_trades).split('T')[0]

            # If we've reached or passed the start_date, we can stop
            if current_end_date <= start_date:
                break
            # throthle this loop
            time.sleep(1)

        if not all_trades:
            return []

        return all_trades


    @redis_cache(expire=86400)  # caches the result for 1 day
    def get_company_news( self, ticker, end_date: str | None, start_date: str | None = None, limit: int = 500 ) -> list[CompanyNews]:
        """Fetch company news from cache or API."""
        #if cached_data := _cache.get_company_news(ticker):
            # Filter cached data by date range
        #    filtered_data = [CompanyNews(**news) for news in cached_data
        #                    if (start_date is None or news["date"] >= start_date)
        #                    and news["date"] <= end_date]
        #    filtered_data.sort(key=lambda x: x.date, reverse=True)
        #    if filtered_data:
        #        return filtered_data

        # If not in cache or insufficient data, fetch from API
        headers = {}
        if self.key:
            headers["X-API-KEY"] = self.key

        url = "https://api.financialdatasets.ai/news/"

        # Build params list
        params = {
            "ticker": ticker,
            "limit": limit
        }

        if start_date:
            params["start_date"] = start_date

        if end_date:
            params["end_date"] = end_date

        all_news = []

        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

            data = response.json()
            response_model = CompanyNewsResponse(**data)
            company_news = response_model.news
            # see https://docs.financialdatasets.ai/api-reference/endpoint/news/company

            if not company_news:
                break

            all_news.extend(company_news)

            # Only continue pagination if we have a start_date or end_date
            #len(company_news)
            if not start_date or not end_date:
                break

            if len(company_news) < limit:
                break

            first_date, last_date = extract_date_limits(data, 'news')
            params["end_date"] = first_date

            logger.info("First date articles: %s", first_date)
            logger.info("Last date articles : %s", last_date)
            logger.info("total articles: %d", len(company_news))

            # If we've reached or passed the start_date, we can stop
            if convert_to_date(first_date) >= convert_to_date(end_date):
                break

            # throthle this loop, it hits the rpm limiter
            time.sleep(1)

        if not all_news:
            return []
        logger.info("ALL news articles count: %d", len(all_news))

        return all_news

    def get_market_cap( self, ticker, end_date: str, ) -> float | None:
        """Fetch market cap from the API."""
        financial_metrics = self.get_financial_metrics(ticker, end_date)
        #market_cap = financial_metrics[0].market_cap
        market_cap = financial_metrics[0].get('market_cap')
        pprint(market_cap)
        if not market_cap:
            return None

        return market_cap

    def prices_to_df(self, prices: list[Price]) -> pd.DataFrame:
        """Convert prices to a DataFrame."""
        df = pd.DataFrame([p.model_dump() for p in prices])
        df["Date"] = pd.to_datetime(df["time"])
        df.set_index("Date", inplace=True)
        numeric_cols = ["open", "close", "high", "low", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.sort_index(inplace=True)
        pprint(df)
        return df

    def prices_to_df_alt2(self, prices: list) -> pd.DataFrame:
        """Convert prices to a DataFrame."""
        #logger.debug(prices)
        #logger.debug(type(prices))
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
                    debug_variable_type(e)
                    debug_variable_type(p)
                    raise ValueError(f"Unable to parse price string: {p}") from e
            else:
                debug_variable_type(p,'{p}')
                debug_variable_type(p)
                raise TypeError(f"Unrecognized price format: {p}")

        df = pd.DataFrame(processed_prices)
        df["Date"] = pd.to_datetime(df["time"])
        df.set_index("Date", inplace=True)
        numeric_cols = ["open", "close", "high", "low", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.sort_index(inplace=True)
        return df

    def prices_to_df_alt(self,prices_input) -> pd.DataFrame:
        """
        Convert price data to a DataFrame.

        The input can be:
          - A PriceResponse object,
          - A dict with a "prices" key, or
          - A list of Price objects (or dicts).

        It expects each record to have a 'time' field (string) in ISO 8601 format.
        """
        # If input is a PriceResponse object, extract the list of Price objects.
        if isinstance(prices_input, PriceResponse):
            prices = prices_input.prices
        # If input is a dict with a "prices" key, extract the list.
        elif isinstance(prices_input, dict) and "prices" in prices_input:
            prices = prices_input["prices"]
        else:
            # Otherwise, assume it's already a list.
            prices = prices_input

        # Convert each record to a dict.
        records = [p.model_dump() if hasattr(p, "model_dump") else p for p in prices]
        df = pd.DataFrame(records)

        # Check if the expected time field exists.
        if "time" in df.columns:
            time_field = "time"
        elif "date" in df.columns:
            time_field = "date"
        else:
            raise KeyError("No 'time' or 'date' field found in the records.")

        # Convert the time field to datetime and set as index.
        df["Date"] = pd.to_datetime(df[time_field])
        df.set_index("Date", inplace=True)

        # Convert numeric columns to numeric types.
        for col in ["open", "close", "high", "low", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df.sort_index(inplace=True)
        #logger.info("debug df:")
        #logger.debug(df)
        logger.debug(type(df))
        logger.debug("df len : %d",len(df))

        return df

    def prices_to_df_alt3(self, prices: list) -> pd.DataFrame:
        """
        Convert price data to a DataFrame.

        The input `prices` can be either:
          - A list of Price objects or dicts, or
          - A dict containing a key "prices" with the list of records.

        Each record is expected to have a date field stored under "time" or "date".
        """
        #logger.debug("prices1: ")
        #logger.debug(prices)
        #logger.debug(type(prices))
        #logger.debug("prices1 %d",len(prices))

        # If the input is a dict with a "prices" key, extract the list
        if isinstance(prices, dict) and "prices" in prices:
            prices = prices["prices"]

        #logger.debug("prices: ")
        #logger.debug(prices)
        #logger.debug(type(prices))
        #logger.debug("prices %d",len(prices))
        # Convert each record to a dict. If it's a Price model, use .model_dump(); otherwise, assume it's already a dict.
        records = [p.model_dump() if hasattr(p, "model_dump") else p for p in prices]
        df = pd.DataFrame(records)

        #logger.debug("records: ")
        #logger.debug(records)
        #logger.debug(type(records))
        #logger.debug("records %d",len(records))

        #logger.debug("df: ")
        #logger.debug(df)
        logger.debug(type(df))
        logger.debug("df %d",len(df))

        # Determine which field to use for the date/time
        if "time" in df.columns:
            time_field = "time"
        elif "date" in df.columns:
            time_field = "date"
        else:
            raise KeyError("No time or date field found in the records.")

        # Convert the time field to datetime and set as index
        df["Date"] = pd.to_datetime(df[time_field])
        df.set_index("Date", inplace=True)

        # Convert numeric columns
        numeric_cols = ["open", "close", "high", "low", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df.sort_index(inplace=True)
        return df

    # Update the get_price_data function to use the new functions
    def get_price_data(self, ticker, start_date: str, end_date: str) -> pd.DataFrame:
        prices = self.get_prices(ticker, start_date, end_date)
        #logger.debug(prices)
        #logger.debug(type(prices))
        return self.prices_to_df_alt(prices)

    def get_ledger(self):
        raise NotImplementedError("Financials.AI client does not implement get_ledger")

    def positions(self):
        raise NotImplementedError("Financials.AI client does not implement positions")

    def get_portfolio(self):
        raise NotImplementedError("Financials.AI client does not implement positions")

    def portfolio_to_df(self):
        raise NotImplementedError("Financials.AI client does not implement positions")
