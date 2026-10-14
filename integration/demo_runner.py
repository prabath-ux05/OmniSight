"""OmniSight Demo Site Runner & Reachability Integration Utility.

Defines the expected OmniSight demo inspection states (clean, overflow,
missing, image, all), URL builders with existing query parameters, and
reachability validation utilities for the controlled demo test target.
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Optional, Sequence, Union
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class DemoInspectionState(str, Enum):
    """Supported OmniSight demo inspection states."""

    CLEAN = "clean"
    OVERFLOW = "overflow"
    MISSING = "missing"
    IMAGE = "image"
    ALL = "all"


# Ordered sequence of all supported inspection states
SUPPORTED_STATES: tuple[DemoInspectionState, ...] = (
    DemoInspectionState.CLEAN,
    DemoInspectionState.OVERFLOW,
    DemoInspectionState.MISSING,
    DemoInspectionState.IMAGE,
    DemoInspectionState.ALL,
)

# Query parameters conforming to demo_site's URL parameter specification:
# - clean: ?state=clean
# - overflow: ?defect=overflow
# - missing: ?defect=missing
# - image: ?defect=image
# - all: ?defects=all
STATE_QUERY_PARAMS: dict[DemoInspectionState, dict[str, str]] = {
    DemoInspectionState.CLEAN: {"state": "clean"},
    DemoInspectionState.OVERFLOW: {"defect": "overflow"},
    DemoInspectionState.MISSING: {"defect": "missing"},
    DemoInspectionState.IMAGE: {"defect": "image"},
    DemoInspectionState.ALL: {"defects": "all"},
}

# String-keyed mapping for quick lookup
_STRING_QUERY_PARAMS: dict[str, dict[str, str]] = {
    state.value: params for state, params in STATE_QUERY_PARAMS.items()
}


def _normalize_state(state: Union[str, DemoInspectionState]) -> DemoInspectionState:
    """Normalize input state into a DemoInspectionState enum instance."""
    if isinstance(state, DemoInspectionState):
        return state

    if not isinstance(state, str):
        raise TypeError(f"State must be a string or DemoInspectionState, got {type(state).__name__}")

    cleaned = state.strip().lower()
    try:
        return DemoInspectionState(cleaned)
    except ValueError:
        valid_states = [s.value for s in DemoInspectionState]
        raise ValueError(
            f"Unsupported demo inspection state: '{state}'. "
            f"Expected one of: {valid_states}"
        ) from None


def construct_demo_url(
    base_url: str,
    state: Union[str, DemoInspectionState],
) -> str:
    """Construct the demo-site URL for a given inspection state using existing query parameters.

    Args:
        base_url: The base URL of the running demo site (e.g. 'http://127.0.0.1:8080').
        state: One of the supported demo inspection states ('clean', 'overflow', 'missing', 'image', 'all').

    Returns:
        The full URL with the corresponding query parameter appended or updated.

    Raises:
        ValueError: If base_url is empty or if state is not one of the supported states.
    """
    cleaned_base = base_url.strip()
    if not cleaned_base:
        raise ValueError("base_url cannot be empty")

    inspection_state = _normalize_state(state)
    query_params = STATE_QUERY_PARAMS[inspection_state]

    parsed = urlparse(cleaned_base)
    # Ensure scheme is present
    scheme = parsed.scheme or "http"
    netloc = parsed.netloc

    # Handle URLs without scheme like '127.0.0.1:8080'
    if not netloc and parsed.path:
        # If netloc is empty and path has host:port or host, re-parse with scheme
        re_parsed = urlparse(f"{scheme}://{cleaned_base.lstrip('/')}")
        scheme = re_parsed.scheme
        netloc = re_parsed.netloc
        path = re_parsed.path or "/"
    else:
        path = parsed.path or "/"

    # Merge existing query params if any
    existing_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    param_dict = dict(existing_pairs)
    param_dict.update(query_params)
    new_query = urlencode(param_dict)

    return urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


# Alias for construct_demo_url
build_demo_url = construct_demo_url


@dataclass
class DemoReachabilityResult:
    """Structured result containing reachability data for a demo inspection state."""

    state: str
    url: str
    reachable: bool
    status_code: Optional[int] = None
    error: Optional[str] = None

    @property
    def is_reachable(self) -> bool:
        """Alias for reachable."""
        return self.reachable

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a standard dictionary."""
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style key access (e.g. result['reachable'])."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Invalid attribute '{key}' on DemoReachabilityResult")

    def get(self, key: str, default: Any = None) -> Any:
        """Allow dict-style get access."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Return the dictionary keys."""
        return ["state", "url", "reachable", "status_code", "error"]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in result fields."""
        return key in self.keys()


class DemoInspectionReport(list[DemoReachabilityResult]):
    """Structured list container for DemoReachabilityResult items with state-level helpers."""

    def __init__(self, results: Iterable[DemoReachabilityResult] = ()):
        super().__init__(results)

    @property
    def all_reachable(self) -> bool:
        """Return True if all inspected states are reachable, False otherwise."""
        return bool(self) and all(r.reachable for r in self)

    @property
    def states(self) -> list[str]:
        """List all state names present in this report."""
        return [r.state for r in self]

    @property
    def by_state(self) -> dict[str, DemoReachabilityResult]:
        """Return a dictionary of results keyed by inspection state name."""
        return {r.state: r for r in self}

    def get(
        self,
        state: Union[str, DemoInspectionState],
        default: Optional[DemoReachabilityResult] = None,
    ) -> Optional[DemoReachabilityResult]:
        """Get the result for a given inspection state."""
        state_key = state.value if isinstance(state, DemoInspectionState) else str(state).strip().lower()
        return self.by_state.get(state_key, default)

    def to_dict(self) -> dict[str, Any]:
        """Export the full report as a structured dictionary."""
        return {
            "all_reachable": self.all_reachable,
            "states": {r.state: r.to_dict() for r in self},
        }

    def __getitem__(self, item: Any) -> Any:
        """Support lookup by integer index or state name string."""
        if isinstance(item, (str, DemoInspectionState)):
            state_key = item.value if isinstance(item, DemoInspectionState) else str(item).strip().lower()
            if state_key in self.by_state:
                return self.by_state[state_key]
            raise KeyError(f"Inspection state '{item}' not found in report results")
        return super().__getitem__(item)


def validate_demo_state(
    base_url: str,
    state: Union[str, DemoInspectionState],
    timeout: float = 5.0,
) -> DemoReachabilityResult:
    """Validate reachability for a single demo inspection state.

    Args:
        base_url: Base URL of the demo site.
        state: The inspection state to validate.
        timeout: Request timeout in seconds.

    Returns:
        Structured DemoReachabilityResult.
    """
    normalized = _normalize_state(state)
    url = construct_demo_url(base_url, normalized)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OmniSight-DemoRunner/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = getattr(response, "status", 200)
            is_reachable = 200 <= status_code < 400
            return DemoReachabilityResult(
                state=normalized.value,
                url=url,
                reachable=is_reachable,
                status_code=status_code,
                error=None,
            )
    except urllib.error.HTTPError as exc:
        return DemoReachabilityResult(
            state=normalized.value,
            url=url,
            reachable=False,
            status_code=exc.code,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except urllib.error.URLError as exc:
        return DemoReachabilityResult(
            state=normalized.value,
            url=url,
            reachable=False,
            status_code=None,
            error=str(exc.reason),
        )
    except (socket.timeout, TimeoutError):
        return DemoReachabilityResult(
            state=normalized.value,
            url=url,
            reachable=False,
            status_code=None,
            error=f"Connection timed out after {timeout} seconds",
        )
    except Exception as exc:  # pylint: disable=broad-except
        return DemoReachabilityResult(
            state=normalized.value,
            url=url,
            reachable=False,
            status_code=None,
            error=str(exc),
        )


def validate_demo_reachability(
    base_url: str,
    states: Optional[Union[Sequence[Union[str, DemoInspectionState]], str, DemoInspectionState]] = None,
    timeout: float = 5.0,
) -> DemoInspectionReport:
    """Validate that the demo site is reachable at a supplied base URL across inspection states.

    For each state, constructs the corresponding demo-site URL using the existing
    query parameters and performs reachability validation.

    Args:
        base_url: The base URL of the running demo site (e.g. 'http://127.0.0.1:8080').
        states: Sequence of states to validate, a single state, or None to validate
                all supported states (clean, overflow, missing, image, all).
        timeout: Socket connection timeout in seconds.

    Returns:
        Structured DemoInspectionReport (iterable list of DemoReachabilityResult with helper accessors).
    """
    if states is None:
        target_states = list(SUPPORTED_STATES)
    elif isinstance(states, (str, DemoInspectionState)):
        target_states = [states]
    else:
        target_states = list(states)

    results: list[DemoReachabilityResult] = []
    for s in target_states:
        result = validate_demo_state(base_url, s, timeout=timeout)
        results.append(result)

    return DemoInspectionReport(results)


# Aliases for convenience and compatibility
validate_demo_site = validate_demo_reachability
check_demo_reachability = validate_demo_reachability


if __name__ == "__main__":
    import sys

    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
    print(f"Validating OmniSight Demo Site inspection states at: {target_url}\n")
    report = validate_demo_reachability(target_url)

    for item in report:
        status_mark = "PASS" if item.reachable else "FAIL"
        status_info = f"HTTP {item.status_code}" if item.status_code else str(item.error)
        print(f"  [{status_mark}] {item.state.ljust(9)} -> {item.url} ({status_info})")

    print(f"\nOverall Result: {'ALL REACHABLE' if report.all_reachable else 'FAILURES DETECTED'}")
    sys.exit(0 if report.all_reachable else 1)
