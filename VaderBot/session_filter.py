from datetime import datetime
import pytz

def in_session(cfg):
    if not cfg["enabled"]:
        return True

    tz = pytz.timezone(cfg["timezone"])
    now = datetime.now(tz).time()

    start = datetime.strptime(cfg["start"], "%H:%M").time()
    end = datetime.strptime(cfg["end"], "%H:%M").time()

    return start <= now <= end