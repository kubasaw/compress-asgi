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
    class StarletteHeaders:
        """
        An immutable, case-insensitive multidict.
        """

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

    class MutableHeaders(StarletteHeaders):
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


class Headers(StarletteHeaders):
    def getacceptedencodings(self) -> dict[str, typing.Optional[float]]:
        user_accepted_encodings = {
            enc: q and float(q)
            for enc, _, q in (
                encoding.partition(";q=")
                for encoding in self.get("accept-encoding", "").split(",")
            )
        }

        return user_accepted_encodings
