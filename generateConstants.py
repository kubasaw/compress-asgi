import urllib.request
import json
import black
import pathlib


with urllib.request.urlopen(
    "https://github.com/jshttp/mime-db/raw/master/db.json"
) as db_handle, open(
    pathlib.Path(__file__).parent / "compress_asgi" / "constants.py", "w"
) as file_handle:
    db: dict[str, dict] = json.load(db_handle)

    compressibleMimes = filter(lambda k: db[k].get("compressible", False), db)
    c = "\n".join(
        (
            "DEFAULT_MINIMUM_SIZE = 500",
            f"DEFAULT_MIMES_INCLUDED = {tuple(compressibleMimes)}",
        )
    )

    file_handle.write(black.format_str(c, mode=black.Mode()))
