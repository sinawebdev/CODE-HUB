"""Feature modules, listed in dependency order (a module may use the services of modules above it)."""
import importlib

MODULES = (
    "platform",
    "media",
    "identity",
    "profiles",
    "network",
    "companies",
    "opportunities",
    "feed",
    "stories",
    "messaging",
    "notifications",
    "search",
    "admin",
    "analytics",
)


def load_models() -> None:
    """Import every module's models so Base.metadata knows all tables (Alembic, tests, CLI)."""
    for name in MODULES:
        importlib.import_module(f"app.modules.{name}.models")
