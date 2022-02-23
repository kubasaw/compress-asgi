# Copyright © 2018, Encode OSS Ltd. All rights reserved.
# https://github.com/encode/starlette/
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import typing

T = typing.TypeVar("T")


class Headers(typing.Mapping[bytes, bytes]):
    """
    An immutable, case-insensitive multidict.
    """

    def __init__(self, headers: typing.Iterable[typing.Tuple[bytes, bytes]]) -> None:
        self._list = headers

    def get(self, key: bytes, default: T = None) -> bytes | T:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: bytes) -> bytes:
        for header_key, header_value in self._list:
            if header_key == key:
                return header_value
        raise KeyError(key)

    def __contains__(self, key: bytes) -> bool:
        for header_key, header_value in self._list:
            if header_key == key:
                return True
        return False

    def __iter__(self) -> typing.Iterator[bytes]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)


class MutableHeaders(Headers):
    def __setitem__(self, key: bytes, value: bytes) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """

        found_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (key, value)
        else:
            self._list.append((key, value))

    def __delitem__(self, key: bytes) -> None:
        """
        Remove the header `key`.
        """

        pop_indexes = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == key:
                pop_indexes.append(idx)

        for idx in reversed(pop_indexes):
            del self._list[idx]

    def add_vary_header(self, vary: bytes) -> None:
        existing = self.get(b"vary")
        if existing is not None:
            vary = b", ".join([existing, vary])
        self[b"vary"] = vary
