"""Navigation package."""

__all__ = ["BrowserNavigator", "NavigationResult"]


def __getattr__(name):
    if name in __all__:
        from .navigator import BrowserNavigator, NavigationResult

        return {
            "BrowserNavigator": BrowserNavigator,
            "NavigationResult": NavigationResult,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")