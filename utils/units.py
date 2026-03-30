def n(val, default=0):
    """Return default if val is None."""
    return val if val is not None else default


def to_f(c):
    """Convert Celsius to Fahrenheit. Returns 0 if value is None."""
    return round((float(c) * 9 / 5) + 32, 1) if c is not None else 0

def to_mph(ms):
    """Convert metres per second to miles per hour. Returns 0 if value is None."""
    return round(float(ms) * 2.237, 1) if ms is not None else 0

def to_inches(mm):
    """Convert millimetres to inches. Returns 0 if value is None."""
    return round(float(mm) / 25.4, 2) if mm is not None else 0

def to_inhg(mbar):
    """Convert millibars (hPa) to inches of mercury. Returns 0 if value is None."""
    return round(float(mbar) * 0.02953, 2) if mbar is not None else 0
