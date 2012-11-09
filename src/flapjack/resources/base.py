# -*- coding: utf-8 -*-
"""
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import, division
import operator
from collections import Sequence, Mapping
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls import patterns, url
import six
from .. import http, utils, authentication, exceptions, encoders


class Meta(type):
    """
    """

    def __new__(cls, name, bases, attrs):
        """
        """
        # six.with_metaclass(..) adds an extra class called `NewBase` in the
        # inheritance tree: Resource > NewBase > object; ignore `NewBase`.
        parents = []
        for base in bases:
            if isinstance(base, Meta) and base.__name__ != 'NewBase':
                parents.append(base)

        if not parents or name == 'NewBase':
            # ignored type or not a subclass of `Resource`.
            return super(Meta, cls).__new__(cls, name, bases, attrs)

        # construct the class object.
        obj = super(Meta, cls).__new__(cls, name, bases, attrs)

        #! Name of the resource to use in URIs; defaults to `__name__.lower()`.
        obj.name = getattr(obj, 'name', obj.__name__.lower())

        #! List of understood HTTP methods.
        obj.http_method_names = utils.config_fallback(getattr(obj,
            'http_method_names', None), 'http.methods', (
                'get',
                'post',
                'put',
                'delete',
                'patch',
                'options',
                'head',
                'connect',
                'trace',
            ))

        #! List of allowed HTTP methods.
        obj.http_allowed_methods = getattr(obj, 'http_allowed_methods', (
                'get',
                'post',
                'put',
                'delete',
            ))

        #! List of allowed HTTP methods against a whole resource (eg /user).
        #! If undeclared or None, will be defaulted to `http_allowed_methods`.
        obj.http_list_allowed_methods = getattr(obj,
            'http_list_allowed_methods', obj.http_allowed_methods)

        #! List of allowed HTTP methods against a single resource (eg /user/1).
        #! If undeclared or None, will be defaulted to `http_allowed_methods`.
        obj.http_detail_allowed_methods = getattr(obj,
            'http_detail_allowed_methods', obj.http_allowed_methods)

        #! List of allowed operations.
        #! Resource operations are meant to generalize and blur the differences
        #! between "PATCH and PUT", "PUT = create / update", etc.
        obj.allowed_operations = getattr(obj, 'allowed_operations', (
                'read',
                'create',
                'update',
                'destroy',
            ))

        #! List of allowed operations against a whole resource.
        #! If undeclared or None, will be defaulted to `allowed_operations`.
        obj.list_allowed_operations = getattr(obj,
            'list_allowed_operations', obj.allowed_operations)

        #! List of allowed operations against a single resource.
        #! If undeclared or None, will be defaulted to `allowed_operations`.
        obj.detail_allowed_operations = getattr(obj,
            'detail_allowed_operations', obj.allowed_operations)

        #! Mapping of encoders known by this resource.
        obj.encoders = utils.config_fallback(getattr(obj, 'encoders', None),
            'encoders', {
                    'json': 'flapjack.encoders.Json'
                })

        #! List of allowed encoders of the understood encoders.
        obj.allowed_encoders = getattr(obj, 'allowed_encoders', (
                'json',
            ))

        #! List of allowed encoders of the understood encoders.
        obj.default_encoder = utils.config_fallback(getattr(obj,
            'default_encoder', None), 'default.encoder',
            obj.encoders[obj.encoders.keys()[0]])

        #! Authentication protocol to use to authenticate access to the
        #! resource.
        obj.authentication = utils.config_fallback(
            getattr(obj, 'authentication', None), 'resource.authentication', (
                    'flapjack.authentication.Authentication',
                ))

        # Ensure certain properties that may be name qualified instead of
        # class objects are resolved to be class objects.
        test = lambda x: isinstance(x, six.string_types)
        for_all = utils.for_all
        for name in (
                    'encoders',
                    'authentication',
                ):
            setattr(obj, name, for_all(getattr(obj, name), utils.load, test))

        # Ensure things that need to be instantied are instantiated
        method = lambda x: x()
        for name in (
                    'encoders',
                    'authentication',
                ):
            setattr(obj, name, for_all(getattr(obj, name), method, callable))

        # return the constructed object; wipe off the magic -- not really.
        return obj


class BaseResource(object):
    """
    """

    @classmethod
    def url(cls, path=''):
        """Builds a url pattern using the passed `path` for this resource."""
        return url(
            r'^{}{}/??(?:\.(?P<format>[^/]*?))?/?$'.format(cls.name, path),
            cls.view,
            name='api_view',
            kwargs={'resource': cls.name},
        )

    @utils.classproperty
    @utils.memoize
    def urls(cls):
        """Builds the complete URL configuration for this resource."""
        return patterns('',
            cls.url(),
            cls.url(r'/(?P<identifier>[^/]+?)'),
            cls.url(r'/(?P<identifier>[^/]+?)/(?P<path>.*?)'),
        )

    @classmethod
    @csrf_exempt
    def view(cls, request, *args, **kwargs):
        """
        Entry-point of the request cycle; handles resource creation and
        delegation.
        """
        try:
            # Traverse path segments; determine final resource
            segments = kwargs.get('path', '').split('/')
            segments = [x for x in segments if x]
            resource = cls.traverse(segments)

            # Instantiate the resource
            obj = resource(request,
                identifier=kwargs.get('identifier'),
                format=kwargs.get('format'))

            # Initiate the dispatch cycle and return its result
            return obj.dispatch()

        except exceptions.Error as ex:
            # Some known error was thrown; give an encoder to the exception
            # and encode an exception response.
            return ex.encode(None)

        except BaseException:
            if settings.DEBUG:
                # TODO: Something went wrong; return the encoded error message.
                # For now; re-raise the erorr.
                raise

            # TODO: Notify system administrator of error
            # Return an empty body indicative of a server failure.
            return http.Response(status=http.INTERNAL_SERVER_ERROR)

    @classmethod
    def traverse(cls, segments):
        """
        """
        if not segments:
            # No sub-resource path provided; return our cls
            return cls

    def __init__(self, request, **kwargs):
        """
        """
        #! Django WSGI request object.
        self.request = request

        #! Identifier of the resource if we are being accessed directly.
        self.identifier = kwargs.get('identifier')

        #! Explicitly declared format of the request.
        self.format = kwargs.get('format')

        #! Encoder that is used for the cycle of the request.
        self._encoder = None

    def dispatch(self):
        """
        """
        try:
            # Assert authentication and attempt to get a valid user object.
            for auth in self.authentication:
                user = auth.authenticate(self.request)
                if user is None:
                    # A user object cannot be retrieved with this
                    # authn protocol.
                    continue

                if user.is_authenticated() or auth.allow_anonymous:
                    # A user object has been successfully retrieved.
                    self.request.user = user
                    break

            else:
                # A user was declared unauthenticated with some confidence.
                raise auth.Unauthenticated

            # Detect an appropriate encoder.
            self._determine_encoder()

            # TODO: Determine decoder

            # Determine the HTTP method
            function = self._determine_method()

            # TODO: Assert resource-level authorization
            # TODO: Decode the request body (if non-empty)
            # TODO: Run clean cycle over decoded body (if non-empty body)
            # TODO: Assert object-level authorization (if non-empty body)

            # Delegate to the determined function.
            data = function()

            # Run prepare cycle over the returned data.
            # data = self.prepare(data)

            # TODO: Build the response object
            # TODO: Apply pagination (?)
            # TODO: Return the response object
            return http.Response(str(data), status=http.OK)

        except exceptions.Error as ex:
            # Known error occured; encode it and return the response.
            # print(repr(ex), ex.encode, self._encoder)
            return ex.encode(self._encoder or self.default_encoder)

    @property
    def _allowed_methods(self):
        """Retrieves a list of allowed HTTP methods for the current request.
        """
        if self.identifier is not None:
            return self.http_detail_allowed_methods

        else:
            return self.http_list_allowed_methods

    def _determine_method(self):
        """Determine the actual HTTP method being used and if it is acceptable.
        """
        if 'HTTP_X_HTTP_METHOD_OVERRIDE' in self.request.META:
            # Someone is using a client that isn't smart enough to send proper
            # verbs; but can still send headers.
            method = self.request.META['HTTP_X_HTTP_METHOD_OVERRIDE'].lower()
            self.request.method = method.upper()

        else:
            # Halfway intelligent client; proceed as normal.
            method = self.request.method.lower()

        if method not in self.http_method_names:
            # Method not understood by our library; die.
            raise exceptions.NotImplemented()

        if method not in self._allowed_methods:
            # Method is not in the list of allowed HTTP methods for this
            # access of the resource.
            allowed = (m.upper() for m in self._allowed_methods)
            raise exceptions.MethodNotAllowed(', '.join(allowed).strip())

        function = getattr(self, self.request.method.lower(), None)
        if function is None:
            # Method understood and allowed but not implemented; stupid us.
            raise exceptions.NotImplemented()

        # Method is just fine; toss 'er back
        return function

    def _determine_encoder(self):
        """Determine the encoder to use according to the request object.
        """
        accept = self.request.META['HTTP_ACCEPT']
        if self.format is not None:
            # An explicit form was supplied; attempt to get it directly
            name = self.format.lower()
            if name in self.allowed_encoders:
                self._encoder = self.encoders.get(name)
                if self._encoder is not None:
                    # Found an appropriate encoder; we're done
                    return

        elif accept is not None and accept.strip() != '*/*':
            for name in self.allowed_encoders:
                encoder = self.encoders[name]
                if encoder.can_transcode(self.request.META['HTTP_ACCEPT']):
                    # Found an appropriate encoder; we're done
                    self._encoder = encoder
                    return

        else:
            # Neither `.fmt` nor an accept header was specified
            self._encoder = self.encoders.get(self.default_encoder)
            return

        # Failed to find an appropriate encoder
        # Get dictionary of available formats
        allowed = self.allowed_encoders
        available = {n: self.encoders[n].mimetype for n in allowed}

        # Encode the response using the appropriate exception
        self._encoder = encoders.Json()  # TODO: Switch to Text when available.
        raise exceptions.NotAcceptable(available)


class Resource(six.with_metaclass(Meta, BaseResource)):
    pass
