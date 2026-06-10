"""UI components for ROG Control."""

__all__ = ["RogControlApp"]


def __getattr__(name: str):
    if name == "RogControlApp":
        from src.ui.app import RogControlApp

        return RogControlApp
    raise AttributeError(name)
