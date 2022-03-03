import builtins
import os.path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(params=(True, False), autouse=True, ids=("NoDeps", "FullDeps"))
def hide_optional_dependencies(request, monkeypatch):
    OPTIONAL_DEPS = ("starlette", "asgiref", "brotli")
    if request.param:

        import_orig = builtins.__import__

        def mocked_import(name, *args, **kwargs):
            if any(package in name for package in OPTIONAL_DEPS):
                raise ModuleNotFoundError()
            return import_orig(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mocked_import)

    modules_to_hide = tuple(
        module_name
        for module_name in sys.modules
        if any(
            searched_module in module_name
            for searched_module in ("compress_asgi", *OPTIONAL_DEPS)
        )
    )

    for m in modules_to_hide:
        monkeypatch.delitem(sys.modules, m)

    return request.param
