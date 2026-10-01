"""OpenTelemetry tracing setup and decorators for SemanticSearchX."""
from functools import wraps
import time
from typing import Any, Callable

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    trace = None
    Status = None
    StatusCode = None
    OTEL_AVAILABLE = False


def get_tracer(name: str = "semanticsearchx"):
    """Return OpenTelemetry tracer or mock fallback."""
    if OTEL_AVAILABLE and trace:
        return trace.get_tracer(name)
    return None


def trace_span(span_name: str):
    """Decorator to instrument functions with OpenTelemetry tracing spans."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer is None:
                return fn(*args, **kwargs)

            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = fn(*args, **kwargs)
                    if span.is_recording():
                        span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if span.is_recording():
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return decorator
