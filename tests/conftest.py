
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest


@pytest.fixture(scope="session")
def local_server():
    fixture_dir = Path(__file__).parent / "fixtures"

    class TestRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(
                *args,
                directory=str(fixture_dir),
                **kwargs,
            )

        def do_GET(self):
            if self.path.split("?")[0] == "/slow":
                time.sleep(0.2)
                self.path = "/index.html"

            super().do_GET()

        def log_message(self, format, *args):
            # Keep test output clean.
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        TestRequestHandler,
    )

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def local_url(local_server):
    return f"{local_server}/index.html"


@pytest.fixture
def slow_url(local_server):
    return f"{local_server}/slow"
