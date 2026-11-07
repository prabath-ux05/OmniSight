
import ipaddress
import re
from urllib.parse import urlsplit


def validate_url(url: str) -> tuple[bool, str]:
    """Validate the format of an HTTP or HTTPS URL."""

    if not isinstance(url, str) or not url.strip():
        return False, "URL is required"

    url = url.strip()

    if len(url) > 2048:
        return False, "URL is too long"

    if any(char.isspace() or ord(char) < 32 for char in url):
        return False, "URL contains spaces or control characters"

    if "\\" in url:
        return False, "URL contains an invalid character"

    try:
        parsed = urlsplit(url)

        if parsed.scheme.lower() not in ("http", "https"):
            return False, "Only HTTP and HTTPS URLs are supported"

        if not parsed.netloc:
            return False, "URL hostname is missing"

        if parsed.username is not None or parsed.password is not None:
            return False, "URLs containing credentials are not allowed"

        hostname = parsed.hostname

        if not hostname:
            return False, "URL hostname is missing"

        port = parsed.port

        if port is not None and not (1 <= port <= 65535):
            return False, "URL port is invalid"

        try:
            ipaddress.ip_address(hostname)

        except ValueError:
            try:
                hostname = hostname.encode("idna").decode("ascii")
            except UnicodeError:
                return False, "URL hostname is invalid"

            hostname = hostname.rstrip(".")

            if not hostname or len(hostname) > 253:
                return False, "URL hostname is invalid"

            label_pattern = re.compile(
                r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
            )

            labels = hostname.split(".")

            if not all(label_pattern.fullmatch(label) for label in labels):
                return False, "URL hostname is invalid"

        return True, "Valid URL"

    except ValueError:
        return False, "URL format is invalid"


def validate_run_id(run_id: str) -> tuple[bool, str]:
    """Validate a run ID before using it in an artifact path."""

    if not isinstance(run_id, str) or not run_id.strip():
        return False, "run_id is required"

    run_id = run_id.strip()

    if len(run_id) > 64:
        return False, "run_id is too long"

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        return False, "run_id contains invalid characters"

    return True, "Valid run_id"
