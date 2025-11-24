def validate_case(case):
    if not isinstance(case, dict):
        raise ValueError("Case must be a dictionary.")
    if "text" not in case:
        raise ValueError("Case must include a 'text' field.")
