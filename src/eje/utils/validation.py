def validate_case(case):
    """
    Validate case input to prevent injection attacks and ensure data integrity.

    Args:
        case: Dictionary containing the case to evaluate

    Raises:
        ValueError: If validation fails
        TypeError: If case is not a dictionary

    Returns:
        bool: True if validation passes
    """
    # Type check
    if not isinstance(case, dict):
        raise TypeError("Case must be a dictionary, got {}".format(type(case).__name__))

    # Required field check
    if "text" not in case:
        raise ValueError("Case must include a 'text' field")

    # Text validation
    text = case.get("text")
    if not isinstance(text, str):
        raise TypeError("'text' field must be a string, got {}".format(type(text).__name__))

    # Prevent excessively long inputs (DoS protection)
    MAX_TEXT_LENGTH = 50000  # ~50KB of text
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Input text too long: {len(text)} characters (max: {MAX_TEXT_LENGTH})"
        )

    # Prevent empty inputs
    if len(text.strip()) == 0:
        raise ValueError("Input text cannot be empty or whitespace-only")

    # Validate allowed keys (prevent injection of unexpected fields)
    ALLOWED_KEYS = {'text', 'context', 'metadata', 'tags', 'priority'}
    invalid_keys = set(case.keys()) - ALLOWED_KEYS
    if invalid_keys:
        raise ValueError(f"Invalid keys in case: {invalid_keys}. Allowed: {ALLOWED_KEYS}")

    # Validate optional context field
    if 'context' in case:
        if not isinstance(case['context'], dict):
            raise TypeError("'context' field must be a dictionary")

    # Validate optional metadata field
    if 'metadata' in case:
        if not isinstance(case['metadata'], dict):
            raise TypeError("'metadata' field must be a dictionary")

    # Validate optional tags field
    if 'tags' in case:
        if not isinstance(case['tags'], list):
            raise TypeError("'tags' field must be a list")
        for tag in case['tags']:
            if not isinstance(tag, str):
                raise TypeError("All tags must be strings")

    return True
