# Copyright © 2018, Encode OSS Ltd. All rights reserved.
# https://github.com/encode/starlette/blob/b032e07f6a883c0de2445fd5953a323ec43a94ed/starlette/datastructures.py
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import typing

try:
    from starlette.datastructures import Headers as StarletteHeaders, MutableHeaders
except ModuleNotFoundError:
    class StarletteHeaders(typing.Mapping[str, str]):
        """
        An immutable, case-insensitive multidict.
        """

        def __init__(
            self,
            headers: typing.Optional[typing.Mapping[str, str]] = None,
            raw: typing.Optional[typing.List[typing.Tuple[bytes, bytes]]] = None,
            scope: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        ) -> None:
            self._list: typing.List[typing.Tuple[bytes, bytes]] = []
            if headers is not None:
                assert raw is None, 'Cannot set both "headers" and "raw".'
                assert scope is None, 'Cannot set both "headers" and "scope".'
                self._list = [
                    (key.lower().encode("latin-1"), value.encode("latin-1"))
                    for key, value in headers.items()
                ]
            elif raw is not None:
                assert scope is None, 'Cannot set both "raw" and "scope".'
                self._list = raw
            elif scope is not None:
                self._list = scope["headers"]

        @property
        def raw(self) -> typing.List[typing.Tuple[bytes, bytes]]:
            return list(self._list)

        def keys(self) -> typing.List[str]:  # type: ignore
            return [key.decode("latin-1") for key, value in self._list]

        def values(self) -> typing.List[str]:  # type: ignore
            return [value.decode("latin-1") for key, value in self._list]

        def items(self) -> typing.List[typing.Tuple[str, str]]:  # type: ignore
            return [
                (key.decode("latin-1"), value.decode("latin-1"))
                for key, value in self._list
            ]

        def get(self, key: str, default: typing.Any = None) -> typing.Any:
            try:
                return self[key]
            except KeyError:
                return default

        def getlist(self, key: str) -> typing.List[str]:
            get_header_key = key.lower().encode("latin-1")
            return [
                item_value.decode("latin-1")
                for item_key, item_value in self._list
                if item_key == get_header_key
            ]

        def mutablecopy(self) -> "MutableHeaders":
            return MutableHeaders(raw=self._list[:])

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

        def __iter__(self) -> typing.Iterator[typing.Any]:
            return iter(self.keys())

        def __len__(self) -> int:
            return len(self._list)

        def __eq__(self, other: typing.Any) -> bool:
            if not isinstance(other, Headers):
                return False
            return sorted(self._list) == sorted(other._list)

        def __repr__(self) -> str:
            class_name = self.__class__.__name__
            as_dict = dict(self.items())
            if len(as_dict) == len(self):
                return f"{class_name}({as_dict!r})"
            return f"{class_name}(raw={self.raw!r})"

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

        def __delitem__(self, key: str) -> None:
            """
            Remove the header `key`.
            """
            del_key = key.lower().encode("latin-1")

            pop_indexes = []
            for idx, (item_key, item_value) in enumerate(self._list):
                if item_key == del_key:
                    pop_indexes.append(idx)

            for idx in reversed(pop_indexes):
                del self._list[idx]

        def __ior__(self, other: typing.Mapping) -> "MutableHeaders":
            if not isinstance(other, typing.Mapping):
                raise TypeError(
                    f"Expected a mapping but got {other.__class__.__name__}"
                )
            self.update(other)
            return self

        def __or__(self, other: typing.Mapping) -> "MutableHeaders":
            if not isinstance(other, typing.Mapping):
                raise TypeError(
                    f"Expected a mapping but got {other.__class__.__name__}"
                )
            new = self.mutablecopy()
            new.update(other)
            return new

        @property
        def raw(self) -> typing.List[typing.Tuple[bytes, bytes]]:
            return self._list

        def setdefault(self, key: str, value: str) -> str:
            """
            If the header `key` does not exist, then set it to `value`.
            Returns the header value.
            """
            set_key = key.lower().encode("latin-1")
            set_value = value.encode("latin-1")

            for idx, (item_key, item_value) in enumerate(self._list):
                if item_key == set_key:
                    return item_value.decode("latin-1")
            self._list.append((set_key, set_value))
            return value

        def update(self, other: typing.Mapping) -> None:
            for key, val in other.items():
                self[key] = val

        def append(self, key: str, value: str) -> None:
            """
            Append a header, preserving any duplicate entries.
            """
            append_key = key.lower().encode("latin-1")
            append_value = value.encode("latin-1")
            self._list.append((append_key, append_value))

        def add_vary_header(self, vary: str) -> None:
            existing = self.get("vary")
            if existing is not None:
                vary = ", ".join([existing, vary])
            self["vary"] = vary


class Headers(StarletteHeaders):
    def getacceptedencodings(self) -> dict[str, float | None]:
        user_accepted_encodings = {
            enc: q and float(q)
            for enc, _, q in (
                encoding.partition(";q=")
                for encoding in self.get("accept-encoding", "").split(",")
            )
        }

        return user_accepted_encodings
