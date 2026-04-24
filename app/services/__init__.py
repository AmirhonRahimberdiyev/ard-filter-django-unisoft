from importlib import import_module
from pathlib import Path
from pkgutil import walk_packages


def __getattr__(name):
    if name.startswith("_"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    package_path = [str(Path(__file__).resolve().parent)]

    for module_info in walk_packages(package_path, prefix=f"{__name__}."):
        module_name = module_info.name.rsplit(".", 1)[-1]
        if module_name.startswith("_"):
            continue

        module = import_module(module_info.name)
        if hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
