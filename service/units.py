from typing import Union


def bytes_to_human(byte_count: Union[int, float, None], system: str = "IEC") -> str:
    """Convert bytes to a human-readable string.

    system:
      - 'IEC': base 1024 with labels KiB, MiB, GiB, TiB
      - 'SI' : base 1000 with labels KB, MB, GB, TB
    """
    if byte_count is None:
        return "N/A"
    try:
        value = float(byte_count)
    except (ValueError, TypeError):
        return "N/A"
    if value < 0:
        value = 0.0
    if value == 0:
        return "0 B"

    system = (system or "IEC").upper()
    if system == "SI":
        power = 1000.0
        labels = ["B", "KB", "MB", "GB", "TB"]
    else:
        power = 1024.0
        labels = ["B", "KiB", "MiB", "GiB", "TiB"]

    idx = 0
    while value >= power and idx < len(labels) - 1:
        value /= power
        idx += 1
    return f"{value:.2f} {labels[idx]}"


