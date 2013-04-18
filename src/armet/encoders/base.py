# -*- coding: utf-8 -*-
"""
Describes the encoder protocols and generalizations used to
encode objects to a format suitable for transmission.
"""
from __future__ import absolute_import, unicode_literals, division
import abc
import six
import mimeparse
from armet import transcoders


class Encoder(six.with_metaclass(abc.ABCMeta, transcoders.Transcoder)):

    def __init__(self, accept, request, response):
        """
        @params[in] accept
            The accept header specifiying the media type.

        @params[in] response
            The http response class used to instantiate response objects.
        """
        # Parse out any parameters
        mime_type = mimeparse.best_match(self.mimetypes, accept)
        self.params = mimeparse.parse_mime_type(mime_type)[2]

        #! The request and response objects to use.
        self.request = request
        self.response = response

    def can_encode(self, obj=None):
        """Tests this encoder to see if it can encode the passed object.
        """
        try:
            # Attempt to encode the object.
            self.encode(obj)

            # The encoding process is assumed to have succeed.
            return True

        except ValueError:
            # The object was of an unsupported type.
            return False

    def encode(self, data=None):
        """
        Transforms the object into an acceptable format for transmission.

        @throws ValueError
            To indicate this encoder does not support the encoding of the
            specified object.
        """
        if data is not None:
            # Set the appropriate headers.
            self.response['Content-Type'] = self.mimetype
            self.response['Content-Length'] = len(data.encode('utf-8'))

            # Write the encoded and prepared data to the response.
            self.response.write(data)
