from .base import RequestTest
from armet.resources import Resource
from armet.api import Api


class TestAPI(RequestTest):

    def test_register_name_with_resource_attribute(self):
        # Create an example resource to register in the API
        class FooResource:
            name = "bar"

        resource = FooResource

        self.app.register(resource)

        assert self.app._registry['bar'] is resource

    def test_register_name_with_class_name(self):
        class FooResource:
            pass

        resource = FooResource

        self.app.register(resource)

        assert self.app._registry['foo'] is resource

    def test_register_name_with_kwargs(self):
        class FooResource:
            pass

        resource = FooResource

        self.app.register(resource, name="bar")

        assert self.app._registry['bar'] is resource

    def test_40x_exception_debug(self):

        self.app.debug = True

        response = self.get('/unknown-resource')

        assert response.status_code == 404

    def test_internal_server_error(self):

        self.app.debug = True

        class TestResource(Resource):

            def read(self):
                raise Exception("This test raises an exception, and"
                                " prints to the console.")

        self.app.register(TestResource, name="test")

        response = self.get('/test')

        assert response.status_code == 500

    def test_redirect_get(self):
        response = self.get('/get/')
        assert response.status_code == 301
        assert response.headers["Location"].endswith("/get")

    def test_redirect_get_inverse(self):
        self.app.trailing_slash = True

        response = self.get('/get/')
        assert response.status_code == 404

        response = self.get('/get')
        assert response.status_code == 301

    def test_redirect_post(self):
        response = self.post('/post/')
        assert response.status_code == 307
        assert response.headers["Location"].endswith("/post")

    def test_no_content(self):

        class TestResource(Resource):

            def read(self):
                return None

        self.app.register(TestResource, name="test")

        response = self.get('/test')

        assert response.status_code == 204

    def test_route(self):

        self.app.debug = True

        class TestResource(Resource):

            first_name = "Test"
            last_name = "Testerson"

            attributes = {'first_name', 'last_name'}

            def read(self):
                return {"first_name": self.first_name, "last_name": self.last_name}

        self.app.register(TestResource, name="test")

        response = self.get('/test')

        assert response.status_code == 200

    def test_add_subapi(self):

        class PersonalApi(Api):
            pass

        class SubResource(Resource):
            attributes = {'success'}

            def read(self):
                return [{'success': True}]

        # Assert that all methods of accessing an api via name work.
        apis = [
            (Api(expose=True), {'name': 'test'}),
            (Api(expose=True, name='new_test'), {}),
            (PersonalApi(expose=True), {}),
        ]

        for api, kwargs in apis:
            api.register(SubResource, name='endpoint')
            self.app.register_api(api, **kwargs)

        # import ipdb; ipdb.set_trace()
        assert self.get('/test/endpoint').status_code == 200
        assert self.get('/new_test/endpoint').status_code == 200
        assert self.get('/personal/endpoint').status_code == 200
