import logging

def debug_variable_type(var, var_name="variable"):
    """
    Logs the type and value of a given variable at the DEBUG level.

    Args:
        var: The variable to inspect.
        var_name (str): Optional name to identify the variable.
    """
    logging.debug(f"{var_name}: type = {type(var).__name__}, value = {repr(var)}")

# Example usage:
if __name__ == "__main__":
    # Configure logging to display debug messages
    logging.basicConfig(level=logging.DEBUG)

    sample_int = 42
    sample_str = "Hello, World"
    sample_list = [1, 2, 3]
    sample_dict = {"key": "value"}

    debug_variable_type(sample_int, "sample_int")
    debug_variable_type(sample_str, "sample_str")
    debug_variable_type(sample_list, "sample_list")
    debug_variable_type(sample_dict, "sample_dict")
