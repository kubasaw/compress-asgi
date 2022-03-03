import builtins
import os.path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(params=(True, False), autouse=True, ids=("NoDeps", "FullDeps"))
def hide_dev_dependencies(request, monkeypatch):
    if request.param:
        import_orig = builtins.__import__

        def mocked_import(name, *args, **kwargs):
            if any(package in name for package in ("starlette", "asgiref", "brotli")):
                raise ModuleNotFoundError()
            return import_orig(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mocked_import)
