""" ..
"""
from django import http
from django.views.decorators.csrf import csrf_exempt
from django.conf.urls import patterns, url
from django.conf import settings
from . import emitters, exceptions, parsers


class Resource(object):

    #! Default list of allowed HTTP methods.
    http_allowed_methods = [
        'get',
        'post',
        'put',
        'delete',
        # TODO: 'patch',
        # ..
        # TODO: 'head',
        # <http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.4>
        # TODO: 'options'
        # <http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.2>
    ]

    #! Name of the resource to use in URIs; defaults to `__name__.lower()`.
    name = None

    def __init__(self):
        # Initialize name to be the name of the instantiated class if it was
        # not defined in the class definition.
        if self.name is None:
            self.name = self.__class__.__name__.lower()

    def find_emitter(self, request, **kwargs):
        """
        Determines the format to emit to and stores it upon success. Raises
        a proper exception if it cannot.
        """
        # Check locations where format may be defined in order of
        # precendence.
        if kwargs.get('format') is not None:
            # Format was provided through the URL via `.FORMAT`.
            self.emitter = emitters.get_by_name(kwargs['format'])

        else:
            # TODO: Should not have an else here and allow the header even
            # if the format check failed ?
            self.emitter = emitters.get_by_request(request)

        if self.emitter is None:
            # Failed to find an appropriate emitter
            # Get dictionary of available formats
            available = emitters.get_available()

            # TODO: No idea what to emit it with; using JSON for now
            # TODO: This should be a configurable property perhaps ?
            self.emitter = emitters.Json

            # Emit the response using the appropriate exception
            raise exceptions.NotAcceptable(self.emit(available))

    def find_parser(self, request, **kwargs):
        """
        Determines the format to parse to and stores it upon success. Raises
        a proper exception if it cannot.
        """
        self.parser = parsers.get(request)
        if self.parser is None:
            # Failed to find an appropriate parser; we have no idea how to
            # handle the data.
            raise exceptions.UnsupportedMediaType()

    def emit(self, obj=None, status=200):
        """Transforms python objects to an acceptable format for tansmission.
        """
        response = http.HttpResponse(status=status)
        if obj is not None:
            response.content = self.emitter.emit(obj)
            response['Content-Type'] = self.emitter.get_mimetype()
        else:
            # No need to specify the default content-type if we don't
            # have a body.
            del response['Content-Type']
        return response

    def parse(self, request):
        """Transforms recieved data to valid python objects.
        """
        # TODO: anything else to do here ?
        return self.parser.parse(request)

    def check_method(self, method):
        """Ensures method is acceptable; throws appropriate exception elsewise.
        """
        method = method.lower()
        if method not in self.http_allowed_methods or \
                not hasattr(self, method):
            # Nope; not allowed -- need to form an http response containing
            # the allowed methods
            response = http.HttpResponse()

            allow = [m.upper() for m in self.http_allowed_methods]
            response['Allow'] = ', '.join(allow).strip()

            raise exceptions.MethodNotAllowed(response)

        # We're good; continue on

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        # ..
        try:
            # Ensure the request method is present in the list of
            # allowed HTTP methods
            self.check_method(request.method)

            # Request an emitter as early as possible in order to
            # accurately return errors (if accrued).
            self.find_emitter(request, **kwargs)

            # TODO: Authn check
            # TODO: Authz check

            obj = None
            if request.body:
                # Request a parse and proceed to parse the request.
                self.find_parser(request)
                obj = self.parse(request)

                # TODO: Authz check (w/object)

            # Delegate to an appropriate method
            method = getattr(self, request.method.lower())
            return method(request, obj, **kwargs)

            # DEBUG: Returning just what we got
            # return self.emit()

        except exceptions.Error as ex:
            # TODO: We need to emit the error response.
            return ex.response

        except BaseException as ex:
            # TODO: `del response['Content-Type']` needs to generalized
            #       somewhere; its everywhere
            if settings.DEBUG:
                response = self.emit({
                    'name': ex.__class__.__name__,
                    'message': str(ex),
                })
                response.status_code = 501
            else:
                # Return no body
                response = http.HttpResponseServerError()
                del response['Content-Type']
            return response

    def read(self, request, **kwargs):
        raise exceptions.NotImplemented()

    def get(self, request, obj=None, **kwargs):
        # TODO: caching, pagination
        # Delegate to `read` to actually grab a list of items
        items = self.read(request, **kwargs)

        # Emit the list of read items.
        return self.emit(items)

    def post(self, request, obj, **kwargs):
        raise exceptions.NotImplemented()

    def put(self, request, obj, **kwargs):
        raise exceptions.NotImplemented()

    def delete(self, request, obj, **kwargs):
        raise exceptions.NotImplemented()

    @property
    def urls(self):
        """Constructs the URLs that this resource will respond to.
        """
        pattern = '^{}{{}}(?:\.(?P<format>[^/]*?))?/?$'.format(self.name)
        return patterns('',
            url(pattern.format(''), self.dispatch, name='dispatch'),
            url(pattern.format('/(?P<id>.*)'), self.dispatch, name='dispatch')
        )


class Model(Resource):
    """Implementation of `Resource` for django's models.
    """
    #! The class object of the django model this resource is exposing.
    model = None

    def read(self, request, **kwargs):
        # TODO: filtering
        return self.model.objects.all()
