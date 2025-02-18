import os
#import pandas as pd
#from pprint import pprint

from .financials_client import FinancialsAPIClient
from .ibkr_client import IBKRClientWrapper

def get_api_client():
    """
    Factory function to choose the API client.
    If the environment variable USE_IBKR is set to "true" (case-insensitive),
    returns an IBKR client; otherwise, returns the legacy Financials API client.
    """
    use_ibkr = os.getenv("USE_IBKR", "false").lower() == "true"
    if use_ibkr:
        return IBKRClientWrapper()
    else:
        return FinancialsAPIClient()

#    def get_financial_metrics(self, ticker, end_date, period="ttm", limit=10):
#    def get_prices(self, ticker, start_date: str, end_date: str):

# Convenience function for compatibility.
def get_financial_metrics(*args, **kwargs):
    client = get_api_client()
    return client.get_financial_metrics(*args, **kwargs)

def get_prices(*args, **kwargs):
    client = get_api_client()
    return client.get_prices(*args, **kwargs)

def prices_to_df(*args, **kwargs):
    client = get_api_client()
    return client.prices_to_df(*args, **kwargs)

def prices_to_df_alt(*args, **kwargs):
    client = get_api_client()
    return client.prices_to_df_alt(*args, **kwargs)

def portfolio_to_df(*args, **kwargs):
    client = get_api_client()
    return client.portfolio_to_df(*args, **kwargs)

def get_ledger(*args, **kwargs):
    client = get_api_client()
    return client.get_ledger(*args, **kwargs)

def positions(*args, **kwargs):
    client = get_api_client()
    return client.positions(*args, **kwargs)

def get_portfolio(*args, **kwargs):
    client = get_api_client()
    return client.get_portfolio(*args, **kwargs)

def get_company_news(*args, **kwargs):
    client = get_api_client()
    return client.get_company_news(*args, **kwargs)

def get_price_data(*args, **kwargs):
    client = get_api_client()
    return client.get_price_data(*args, **kwargs)

def get_insider_trades(*args, **kwargs):
    client = get_api_client()
    return client.get_insider_trades(*args, **kwargs)

