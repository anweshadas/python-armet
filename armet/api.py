from . import decoders, encoders, http
from armet.http import exceptions
from armet import utils
import traceback


class Api:

    def __init__(self, trailing_slash=True):
        # TODO: Should this be that `Registry` thing we were talking about?
        #       That would give us the `remove` functionality easily
        self._registry = {}

        # Trailing slash handling.
        # The value indicates which URI is the canonical URI and the
        # alternative URI is then made to redirect (with a 301) to the
        # canonical URI.
        self.trailing_slash = trailing_slash

    def reroute(self, request, response):
        """Reroute the user to the correct URI"""
        response.headers['Location'] = request.path + "/"
        if not request.method == "GET":
            response.status_code = 301
            return
        response.status_code = 307

    def setup(self):
        """Called on request setup in the context of this API.
        """

    def teardown(self):
        """Called on request teardown in the context of this API.
        """

    def register(self, handler, *, expose=True, name=None):  # noqa
        # Discern the name of the handler in order to register it.
        if name is None:
            # Convert the name of the handler to dash-case
            name = utils.dasherize(handler.__name__)

            # Strip a trailing '-resource' from it
            if name.endswith("-resource"):
                name = name[:-9]

        # Insert the handler into the registry.
        self._registry[name] = handler

    def __call__(self, environ, start_response):
        """Entry-point from the WSGI environment.

        When a request comes in from a "client" this is the first place
        it goes after it is received by the "server" (uWSGI, nginx, etc.).
        """
        # Create the request and response wrappers around the environ.
        request = http.Request(environ)
        response = http.Response()

        if not self.trailing_slash:
            self.reroute(request, response)
            return response(environ, start_response)
        # Setup the request.
        self.setup()

        # Route the request.. needs a better name for the function perhaps.
        # import ipdb; ipdb.set_trace()
        try:
            self.route(request, response)

        except exceptions.Base as ex:
            # If the exception raised was an error-like exception (4xx or 5xx)
            # then print the traceback as well.
            if ex.status // 100 >= 4:
                traceback.print_exc()

            # An HTTP/1.1 understood exception was raised from somewhere
            # within the request cycle. We Pull the status and headers
            # from the exception object.
            response.headers.extend(ex.headers.items())
            response.status_code = ex.status
            response.set_data(b'')

        # Teardown the request.
        # FIXME: This should happen directly before closing the connection
        #        with the user, not here.
        self.teardown()

        # Invoke the response wrapper to initiate the (possibly streaming)
        # response.
        return response(environ, start_response)

    def get_resource(self, path):
        """Uses the request path to instantiate and return the correct
        resource using the slug and context.
        """

        # Attempt to find the resource through the initial path.
        context = {}
        # import ipdb; ipdb.set_trace()
        segments = list(filter(None, path.split("/")))
        while len(segments) > 2:
            # Pop the (name, slug) pair from the segments list.
            name = segments.pop(0)
            slug = segments.pop(0)

            # Attempt to lookup the resource from the passed name.
            resource_cls = self._registry[path]

            # Instantiate the resource.
            resource = resource_cls(slug=slug, context=context)

            # Invoke `.read` and store it in the context; we are not
            # at the final segment in the url.
            context[name] = resource.read()

        # Grab the final (name, slug?) pair from the list.
        name = segments[0]
        slug = segments[1] if len(segments) > 1 else None

        # Attempt to lookup the resource from the passed name.
        if name not in self._registry:
            raise exceptions.NotFound
        resource_cls = self._registry[name]

        # Instantiate the resource.
        return resource_cls(slug=slug, context=context)

    def decode(self, request):
        # Read in the request data.
        # TODO: Think of a way to expose this (just "content" or "data")
        request_raw_data = request.data
        if request_raw_data:
            # Find an available decoder.
            content_type = request.headers.get("Content-Type")
            if not content_type:
                # TODO: Handle content-type "detection"
                raise exceptions.UnsupportedMediaType()

            try:
                # TODO: The content-type header could state more than just
                #       the mime_type (charset, etc.); think of how to deal
                #       with it as media_range detection "works" with it but
                #       mime_type would be faster.
                decode = decoders.find(media_range=content_type)

                # Decode the incoming request data.
                # TODO: We should likely be sending the proper charset
                #       to ".decode(..)"
                return decode(request_raw_data.decode("utf-8"))

            except (KeyError, TypeError):
                # Failed to find a matching decoder.
                raise exceptions.UnsupportedMediaType()

        # No request data
        return None

    def encode(self, request, response, data):
        # Find an available encoder.
        media_range = request.headers.get("Accept", "application/json")
        if media_range == "*/*":
            media_range = "application/json"

        try:
            encoder = encoders.find(media_range=media_range)

            # Encode the data.
            # TODO: We should be detecting the proper charset and using that
            # instead.
            response.response = encoder(data, 'utf-8')
            response.headers['Content-Type'] = encoder.preferred_mime_type

        except (KeyError, TypeError) as ex:
            # Failed to find a matching encoder.
            raise exceptions.NotAcceptable from ex

    def route(self, request, response):
        # TODO: We need a way to know the content-type here.. or the encoder
        #       needs to handle pushing the content-type.

        # Return an empty 404 if were accessed at "/" (
        # we don't handle this yet).
        if request.path == "/":
            raise exceptions.NotFound()

        # Get the request data
        request_data = self.decode(request)

        # Instantiate the correct resource with
        resource = self.get_resource(request.path)

        # We are at the final segment in the URL; we need to route this
        # dependent on the HTTP/1.1 method.
        try:
            route = getattr(self, request.method.lower())

        except AttributeError:
            raise exceptions.MethodNotAllowed

        # Dispatch the request.
        response_data = route(resource, request_data)

        # Write the response data into the response object
        self.encode(request, response, response_data)

        # Return a successful response.
        response.status_code = 200
        return

    def get(self, resource, data=None):
        items = resource.read()

        if resource.slug is not None:
            try:
                return resource.prepare_item(items[0])

            except TypeError:
                return resource.prepare_item(items)

        return resource.prepare(items)
