from datetime import datetime, timedelta
from pprint import pprint

def convert_to_date(date_str, fmt="%Y-%m-%d", return_type="datetime"):
    """
    Convert a date string to a datetime or date object.

    Parameters:
      date_str (str): The date string.
      fmt (str): The format of the date string (default: "%Y-%m-%d").
      return_type (str): "datetime" to return a datetime object,
                         "date" to return a date object.

    Returns:
      datetime.datetime or datetime.date: The converted date.
    """
    dt = datetime.strptime(date_str, fmt)
    if return_type == "date":
        return dt.date()
    return dt

def convert_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to an ISO formatted string
    raise TypeError(f'Object of type {type(obj).__name__} is not serializable')

def convert_datetimes(obj, fmt="%Y%m%d-%H:%M:%S"):
    """
    Recursively converts datetime objects within a dict or list to a formatted string.
    The desired format is 'YYYYMMDD-HH:mm:ss'.
    """
    if isinstance(obj, datetime):
        return obj.strftime(fmt)
    elif isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(item) for item in obj]
    else:
        return obj

def calculate_bar_period(start_time: str, end_time: str) -> str:
    # Check if start_time or end_time are empty or None.
    pprint(start_time)
    pprint(end_time)

    start_full = convert_date_to_ibkr(start_time, is_start=True)
    end_full = convert_date_to_ibkr(end_time, is_start=False)

    if not start_full:
        raise ValueError("Parameter 'start_time' is empty. Please provide a valid string in the format 'YYYYMMDD-HH:mm:dd'.")
    if not end_full:
        raise ValueError("Parameter 'end_full' is empty. Please provide a valid string in the format 'YYYYMMDD-HH:mm:dd'.")

    # Print input values (for debugging)
    pprint(f"start_full: {start_full}")
    pprint(f"end_full: {end_full}")

    # Try to parse the start_full and end_full; raise an error if the format is incorrect.
    # dt = datetime.strptime(date_str, "%Y%m%d-%H:%M:%S")
    try:
        date_start = datetime.strptime(start_full, "%Y%m%d-%H:%M:%S")
    except ValueError as ve:
        raise ValueError(f"Invalid format for start_full: '{start_full}'. Expected format 'YYYYMMDD-HH:mm:dd'.") from ve

    try:
        date_end = datetime.strptime(end_full, "%Y%m%d-%H:%M:%S")
    except ValueError as ve:
        raise ValueError(f"Invalid format for end_full: '{end_full}'. Expected format 'YYYYMMDD-HH:mm:dd'.") from ve

    # Calculate the difference between the two dates
    diff = date_end - date_start

    # If the difference is less than one day, return hours (ignoring minutes/seconds).
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() // 3600)
        return f"{hours}h"
    else:
        days = diff.days
        return f"{days}d"

def convert_date_to_ibkr(date_str: str, is_start: bool = True) -> str:
    """
    Converts a date string in the format 'YYYY-MM-DD' into a string in the format
    'YYYYMMDD HH:MM:SS'. If is_start is True, uses the market open time;
    otherwise, uses the market close time. TODO: VERIFY THE TIMEZONE STUFF WITH IBKR

    IBKR wants: Value Format: UTC; YYYYMMDD-HH:mm:dd
    FINANCIALS wants :  The start date for the price data (format: YYYY-MM-DD).

    'start_time: 2024-11-09'
    'end_time: 2025-02-09'

    Args:
        date_str (str): The date string in 'YYYY-MM-DD' format.
        is_start (bool): True for start time (market open), False for end time (market close).

    Returns:
        str: The formatted date string with the appropriate time.

    Raises:
        ValueError: If date_str is empty or not in the expected format.
    """
    if not date_str:
        raise ValueError("Input date_str is empty. Please provide a valid date string in 'YYYY-MM-DD' format.")

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format for '{date_str}'. Expected format is 'YYYY-MM-DD'.") from e

    # Set the default times (adjust these as needed)
    market_open = "09:30:00"
    market_close = "16:00:00"
    default_time = market_open if is_start else market_close

    # Format the date as YYYY/MM/DD and append the default time.
    formatted_date = dt.strftime("%Y%m%d")
    return f"{formatted_date}-{default_time}"

def extract_date_limits(json_data, data_key="news", date_field="date", fmt="%Y-%m-%d"):
    """
    Extracts the smallest and largest dates from a JSON result set.

    If json_data is a dict, it looks for a list of records under `data_key`.
    If json_data is already a list, it uses that list directly.
    Each record is expected to have a field named `date_field` in ISO 8601 format 
    (e.g., "2025-02-16T14:30:00Z").

    Parameters:
        json_data (dict or list): The JSON data returned by response.json() or the list of records.
        data_key (str): The key that holds the list of records (default "news").
        date_field (str): The field in each record that contains the date (default "date").
        fmt (str): The output date format (default: "%Y-%m-%d").

    Returns:
        tuple: (min_date_str, max_date_str) formatted as strings,
               or (None, None) if no valid dates are found.
    """
    # If json_data is a dict, extract records using data_key.
    if isinstance(json_data, dict):
        records = json_data.get(data_key, [])
    elif isinstance(json_data, list):
        records = json_data
    else:
        records = []

    dates = []
    for record in records:
        date_str = record.get(date_field) if isinstance(record, dict) else None
        #pprint(date_str)
        if date_str:
            try:
                # Parse the ISO 8601 date string ending with 'Z'
                dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                dates.append(dt)
            except ValueError:
                continue

    if not dates:
        return None, None

    min_date = min(dates)
    max_date = max(dates)
    return min_date.strftime(fmt), max_date.strftime(fmt)


# Example usage:
if __name__ == "__main__":
    start_date_input = "2024-11-09"
    end_date_input = "2025-02-09"

    start_full = convert_date_to_ibkr(start_date_input, is_start=True)
    end_full = convert_date_to_ibkr(end_date_input, is_start=False)

    print("Start time:", start_full)  # e.g., "2024/11/09 09:30:00"
    print("End time:", end_full)      # e.g., "2025/02/09 16:00:00"

    pprint(type(convert_datetimes("2025-01-01 00:00:00")))

    # Example usage:
    d1 = convert_date("2021-12-31")          # Returns a datetime object by default
    d2 = convert_date("2022-01-01", return_type="date")  # Returns a date object

    print(d1)  # e.g. 2021-12-31 00:00:00
    print(d2)  # 2022-01-01

    # Comparisons work as long as you are comparing objects of the same type.
    # If you compare datetime to datetime or date to date, all is well.
    if d1 < convert_date("2022-01-01"):
        print("d1 is before January 1, 2022")

    # Example JSON result set
    sample_json = {
        "data": [
            {"date": "2025-02-16T14:30:00Z", "value": 123},
            {"date": "2025-02-15T10:15:00Z", "value": 456},
            {"date": "2025-02-18T09:00:00Z", "value": 789},
        ]
    }

    min_date, max_date = extract_date_limits(sample_json)
    print("Min date:", min_date)  # e.g., "2025-02-15"
    print("Max date:", max_date)  # e.g., "2025-02-18"

    # Simulated JSON response where the date records are under "news"
    sample_json = {
        "news": [
            {"date": "2025-02-16T14:30:00Z", "headline": "News A"},
            {"date": "2025-02-15T10:15:00Z", "headline": "News B"},
            {"date": "2025-02-18T09:00:00Z", "headline": "News C"},
        ]
    }

    min_date, max_date = extract_date_limits(sample_json)
    print("Min date:", min_date)  # e.g., "2025-02-15"
    print("Max date:", max_date)  # e.g., "2025-02-18"

    # If your JSON uses a different key for records:
    alt_json = {
        "articles": [
            {"timestamp": "2025-03-01T08:00:00Z", "title": "Article 1"},
            {"timestamp": "2025-03-05T12:00:00Z", "title": "Article 2"}
        ]
    }

    min_date, max_date = extract_date_limits(alt_json, data_key="articles", date_field="timestamp", fmt="%Y-%m-%d")
    print("Alt Min date:", min_date)  # "2025-03-01"
    print("Alt Max date:", max_date)  # "2025-03-05"

