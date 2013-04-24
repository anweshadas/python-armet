# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
from armet import http
import io


class Response(http.Response):

    class Headers(http.response.Headers):

        def __init__(self, *args, **kwargs):
            self._store = {}
            super(Response.Headers, self).__init__(*args, **kwargs)

        def __setitem__(self, name, value):
            self._obj._assert_open()
            self._store[self._normalize(name)] = value

        def __getitem__(self, name):
            return self._store[self._normalize(name)]

        def __contains__(self, name):
            return self._normalize(name) in self._store

        def __delitem__(self, name):
            self._obj._assert_open()
            del self._store[self._normalize(name)]

        def __len__(self):
            return len(self._store)

        def __iter__(self):
            return iter(self._store)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('asynchronous', False)
        super(Response, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.content = ''
        self.stream = io.BytesIO()
        self._headers = self.Headers(self)
        self._status = 200
        self._closed = False
        self._streaming = False

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._assert_open()
        self._status = value

    def tell(self):
        return self.stream.tell() + len(self.content)

    def _write(self, chunk):
        self.stream.write(chunk)

    def _flush(self):
        raise NotImplementedError()

    def close(self):
        super(Response, self).close()
        self.content = self.stream.getvalue()