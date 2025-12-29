import json
import sys


def log_event(event: str, **kwargs):
    rec = {"event": event}
    rec.update(kwargs)
    sys.stdout.write(json.dumps(rec) + "\n")
    sys.stdout.flush()
