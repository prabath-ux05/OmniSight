"""Browser agent evidence collection and snapshots."""

try:
    from browser_agent.evidence.dom_capture import DOMCapture
except ImportError:
    from .dom_capture import DOMCapture

__all__ = ["DOMCapture"]

