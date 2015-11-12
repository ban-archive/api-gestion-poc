from uuid import UUID


def is_uuid4(uuid_string):
    """
    Validate that a UUID string is in
    fact a valid uuid4.
    """
    try:
        UUID(uuid_string, version=4)
    except (ValueError, TypeError):
        # If it's a value error, then the string
        # is not a valid hex code for a UUID.
        # None will raise TypeError.
        return False
    return True
