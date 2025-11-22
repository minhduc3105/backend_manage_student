from datetime import datetime, date
from datetime import time, datetime

def to_naive_time(t: str | time) -> time:
    """
    Convert string ISO hoặc datetime.time có tzinfo sang naive time (HH:MM:SS)
    """
    if isinstance(t, time):
        return t.replace(tzinfo=None)
    elif isinstance(t, str):
        # nếu string dạng "04:25:43.964Z" hoặc "04:25:43"
        if t.endswith("Z"):
            t = t[:-1]  # loại bỏ Z
        dt_obj = datetime.fromisoformat(t)
        return dt_obj.time().replace(tzinfo=None)
    return t

def parse_date_safe(d):
    """Chuyển đổi giá trị ngày từ Excel sang date object."""
    if not d:
        return None

    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d

    # Nếu là số serial ngày của Excel
    if isinstance(d, (int, float)):
        try:
            return datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(d) - 2).date()
        except Exception:
            return None

    # Nếu là string
    if isinstance(d, str):
        d = d.strip()
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M:%S").date()
        except Exception:
            pass
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(d, fmt).date()
            except Exception:
                continue

    return None
