__version__ = "0.1.0"

__all__ = [
    "main",
    "DeadlockLauncher",
    "HeroImageExtractor",
    "CrossPlatformController",
    "get_default_game_path",
]


def __getattr__(name):
    if name in __all__:
        from .main import (
            CrossPlatformController,
            DeadlockLauncher,
            HeroImageExtractor,
            get_default_game_path,
            main,
        )

        exported = {
            "main": main,
            "DeadlockLauncher": DeadlockLauncher,
            "HeroImageExtractor": HeroImageExtractor,
            "CrossPlatformController": CrossPlatformController,
            "get_default_game_path": get_default_game_path,
        }
        return exported[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")