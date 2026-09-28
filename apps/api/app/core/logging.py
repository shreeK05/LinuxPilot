import logging
import json
import os
from datetime import datetime, timezone
from pythonjsonlogger.json import JsonFormatter

class CustomJsonFormatter(JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add required blueprint fields if not present
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.now(timezone.utc).isoformat() + "Z"
            
        # Ensure blueprint structure
        for field in ['task_id', 'run_id', 'step_id', 'component', 'event', 'action', 'status', 'latency_ms']:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)

        # Sanitize sensitive payload data if any
        if 'payload' in log_record and isinstance(log_record['payload'], dict):
            sanitized = {}
            for k, v in log_record['payload'].items():
                if k.lower() in ['secret', 'token', 'password', 'key', 'credentials', 'authorization']:
                    sanitized[k] = '***REDACTED***'
                else:
                    sanitized[k] = v
            log_record['payload'] = sanitized

def setup_logging():
    logger = logging.getLogger("linuxpilot")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console Handler with JSON Formatter
    console_handler = logging.StreamHandler()
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

structured_logger = setup_logging()

def log_event(event_type: str, status: str, component: str, task_id: str = None, 
              step_id: str = None, action: str = None, latency_ms: int = None, 
              payload: dict = None, message: str = ""):
    extra = {
        "event": event_type,
        "status": status,
        "component": component
    }
    if task_id: extra["task_id"] = task_id
    if step_id: extra["step_id"] = step_id
    if action: extra["action"] = action
    if latency_ms is not None: extra["latency_ms"] = latency_ms
    if payload: extra["payload"] = payload
    
    # Use standard python logging which will be intercepted by jsonlogger
    structured_logger.info(message or event_type, extra=extra)
