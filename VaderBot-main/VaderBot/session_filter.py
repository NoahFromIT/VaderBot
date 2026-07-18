from datetime import datetime
import pytz

def in_session(cfg):
    if not cfg["enabled"]:
        return True

    tz = pytz.timezone(cfg["timezone"])
    now = datetime.now(tz).time()

    start = datetime.strptime(cfg["start"], "%H:%M").time()
    end = datetime.strptime(cfg["end"], "%H:%M").time()

    if start <= end:
        return start <= now <= end
    else:
        # Handles sessions spanning midnight, e.g., start at 18:00 and end at 17:00 next day
        return now >= start or now <= end