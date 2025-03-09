from urllib.parse import urlparse

def is_valid_url(url):
    try:
        result = urlparse(url)
        # Check that the scheme and network location are non-empty
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
