import logging
import json
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        
        # Add any extra attributes passed via 'extra'
        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id
        if hasattr(record, 'step_id'):
            log_data['step_id'] = record.step_id
        if hasattr(record, 'execution_id'):
            log_data['execution_id'] = record.execution_id
        if hasattr(record, 'event'):
            log_data['event'] = record.event
        if hasattr(record, 'status'):
            log_data['status'] = record.status

        return json.dumps(log_data)

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicating logs if setup_logger is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logger("linuxpilot")
