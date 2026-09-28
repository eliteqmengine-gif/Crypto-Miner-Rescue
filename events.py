import json
import asyncio
from datetime import datetime
from typing import Dict, Any
from asyncio import Queue
from pathlib import Path

RISK_LOG = "risk_events.jsonl"

# Global event queue and background worker
_event_queue: Queue = None
_worker_task = None

async def init_event_logger():
    """Initialize the async event logger.
    
    Call this once at application startup.
    """
    global _event_queue, _worker_task
    if _event_queue is None:
        _event_queue = Queue()
        _worker_task = asyncio.create_task(_log_writer())

async def _log_writer():
    """Background worker that writes events to disk.
    
    Runs continuously, batching writes for efficiency.
    """
    buffer = []
    flush_interval = 5  # seconds
    
    async def flush_buffer():
        if buffer:
            try:
                with open(RISK_LOG, "a") as f:
                    for event in buffer:
                        f.write(json.dumps(event) + "\n")
                buffer.clear()
            except IOError as e:
                print(f"Error writing to risk log: {e}")
    
    try:
        while True:
            try:
                # Wait for an event with timeout for periodic flushing
                event = await asyncio.wait_for(
                    _event_queue.get(),
                    timeout=flush_interval
                )
                buffer.append(event)
                
                # Flush if buffer reaches 100 events
                if len(buffer) >= 100:
                    await flush_buffer()
            except asyncio.TimeoutError:
                # Flush periodically even if no events
                await flush_buffer()
    except asyncio.CancelledError:
        # Final flush before shutdown
        await flush_buffer()
        raise

async def log_risk_event(event_type: str, severity: str, details: Dict[str, Any]) -> None:
    """Log a risk event asynchronously.
    
    Non-blocking operation - event is queued and written in background.
    
    Args:
        event_type: Type of risk event (e.g., 'price_spike', 'loss_threshold')
        severity: Severity level ('INFO', 'WARNING', 'CRITICAL')
        details: Dict containing event details
    """
    global _event_queue
    if _event_queue is None:
        raise RuntimeError("Event logger not initialized. Call init_event_logger() first.")
    
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "severity": severity,
        "details": details
    }
    
    await _event_queue.put(event)

def log_risk_event_sync(event_type: str, severity: str, details: Dict[str, Any]) -> None:
    """Synchronous wrapper for log_risk_event (for non-async contexts).
    
    This immediately writes to disk - use log_risk_event() for async contexts.
    
    Args:
        event_type: Type of risk event
        severity: Severity level
        details: Dict containing event details
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "severity": severity,
        "details": details
    }
    try:
        with open(RISK_LOG, "a") as f:
            f.write(json.dumps(event) + "\n")
    except IOError as e:
        print(f"Error writing to risk log: {e}")

async def shutdown_event_logger():
    """Shutdown the async event logger.
    
    Call this during application shutdown to ensure all events are flushed.
    """
    global _event_queue, _worker_task
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _event_queue = None
        _worker_task = None

def get_recent_events(limit: int = 100) -> list:
    """Read recent risk events from log file.
    
    Args:
        limit: Number of most recent events to return
        
    Returns:
        List of risk event dicts, most recent first
    """
    events = []
    try:
        if Path(RISK_LOG).exists():
            with open(RISK_LOG, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            # Return most recent events first
            return events[-limit:] if len(events) > limit else events
    except IOError as e:
        print(f"Error reading risk log: {e}")
    
    return events

def get_events_by_severity(severity: str, limit: int = 100) -> list:
    """Filter risk events by severity level.
    
    Args:
        severity: Severity level to filter by
        limit: Maximum number of events to return
        
    Returns:
        List of matching risk events
    """
    events = []
    try:
        if Path(RISK_LOG).exists():
            with open(RISK_LOG, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if event.get("severity") == severity:
                                events.append(event)
                                if len(events) >= limit:
                                    break
                        except json.JSONDecodeError:
                            continue
    except IOError as e:
        print(f"Error reading risk log: {e}")
    
    return events
