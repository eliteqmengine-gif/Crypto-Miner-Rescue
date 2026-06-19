import json
from datetime import datetime

RISK_LOG = "risk_events.jsonl"

def log_risk_event(event_type, severity, details):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "severity": severity,
        "details": details
    }
    with open(RISK_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
