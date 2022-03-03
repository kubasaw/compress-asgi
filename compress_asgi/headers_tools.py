import typing

try:
    from starlette.datastructures import Headers as StarletteHeaders
    from starlette.datastructures import MutableHeaders
except ModuleNotFoundError:
    StarletteHeaders = None
    MutableHeaders = None

if not StarletteHeaders:

    class StarletteHeaders:
        def __init__(
            self,
            scope: typing.Optional[typing.Mapping[str, typing.Any]],
        ) -> None:
            self._list = scope["headers"]

        def get(self, key: str, default: typing.Any = None) -> typing.Any:
            try:
                return self[key]
            except KeyError:
                return default

        def __getitem__(self, key: str) -> str:
            get_header_key = key.lower().encode("latin-1")
            for header_key, header_value in self._list:
                if header_key == get_header_key:
                    return header_value.decode("latin-1")
            raise KeyError(key)

        def __contains__(self, key: typing.Any) -> bool:
            get_header_key = key.lower().encode("latin-1")
            for header_key, header_value in self._list:
                if header_key == get_header_key:
                    return True
            return False


class Headers(StarletteHeaders):
    @staticmethod
    def parseEncoding(encoding: str):
        enc, sep, q = encoding.partition(";q=")

        try:
            return enc.strip(), float(q)
        except ValueError:
            return enc.strip(), None

    def getacceptedencodings(self):
        accept_encoding_header: str = self.get("accept-encoding")

        if accept_encoding_header:
            user_accepted_encodings = {
                enc: q
                for enc, q in (
                    self.parseEncoding(encoding)
                    for encoding in accept_encoding_header.split(",")
                )
            }
        else:
            user_accepted_encodings = {}

        return user_accepted_encodings


if not MutableHeaders:

    class MutableHeaders(Headers):
        def __setitem__(self, key: str, value: str) -> None:
            """
            Set the header `key` to `value`, removing any duplicate entries.
            Retains insertion order.
            """
            set_key = key.lower().encode("latin-1")
            set_value = value.encode("latin-1")

            found_indexes = []
            for idx, (item_key, item_value) in enumerate(self._list):
                if item_key == set_key:
                    found_indexes.append(idx)

            for idx in reversed(found_indexes[1:]):
                del self._list[idx]

            if found_indexes:
                idx = found_indexes[0]
                self._list[idx] = (set_key, set_value)
            else:
                self._list.append((set_key, set_value))

        def add_vary_header(self, vary: str) -> None:
            existing = self.get("vary")
            if existing is not None:
                vary = ", ".join([existing, vary])
            self["vary"] = vary
