from flask_restful import Resource, request
from api.response import response_decorator, HttpCodes
from api.service.service import *


class Controller(Resource):

    """
    "Abstract class" for all the controllers in the api to implement rest-api methods.
    """

    def post(self, *args, **kwargs):
        """
        Create a new resource on the server
        """
        pass

    def get(self, *args, **kwargs):
        """
        Get an existing resource from the server
        """
        pass

    def put(self, *args, **kwargs):
        """
        Update an existing resource on the server
        """
        pass

    def delete(self, *args, **kwargs):
        """
        Delete an existing resource from the server
        """
        pass


class UserController(Controller):
    """
    User controller to interact with the client requests.
    """
    def __init__(self, user_service_implementation, user_model):
        """
        Init the controller class

        Args:
            user_service_implementation (UserServiceImplementation): a class that implements the user service.
            user_model (UserModel): a user model to interact with DB operations.
        """
        self._user_service_implementation = user_service_implementation
        self._user_model = user_model

    @response_decorator(code=HttpCodes.OK)
    def post(self):
        """
        Endpoint to create a new user on the server.

        Returns:
            dict: a new user response to the client.
        """
        print("endpoints:response_decorator, request:", request)
        print("endpoints:response_decorator, json:", request.json)
        rule = request.url_rule
        # print(rule, ",", str(rule))

        if "Attacks" in str(rule):
            return ServiceClassWrapper(
                class_type=self._user_service_implementation,
                model=self._user_model
            ).attacks(**request.json)

        if "Login" in str(rule):
            return ServiceClassWrapper(
                class_type=self._user_service_implementation,
                model=self._user_model
            ).get_one(**request.json)

        if "check_session" in request.json:
            print("calling check_session")
            return ServiceClassWrapper(
                class_type=self._user_service_implementation,
                model=self._user_model
            ).check_session(**request.json)
        else:
            return ServiceClassWrapper(
                class_type=self._user_service_implementation,
                model=self._user_model
            ).create(**request.json)

    @response_decorator(code=HttpCodes.OK)
    def get(self, username=None, password=None):
        """
        Endpoint to get an existing user from the server.

        Args:
            username (str): a user name from the URL.
            password (str): a user password from the URL.

        Returns:
            dict/list[dict]: Returns either all users or a single user.
        """
        if username:  # get single user
            pass
            # return ServiceClassWrapper(
            #     class_type=self._user_service_implementation,
            #     model=self._user_model
            # ).get_one(username=username, password=password)
        else:  # get all users
            return ServiceClassWrapper(
                class_type=self._user_service_implementation,
                model=self._user_model
            ).get_many()

    @response_decorator(code=HttpCodes.NO_CONTENT)
    def put(self, username):
        """
        Endpoint to update an existing user in the server.
        """
        return ServiceClassWrapper(
            class_type=self._user_service_implementation, model=self._user_model
        ).update(username=username, **request.json)

    @response_decorator(code=HttpCodes.NO_CONTENT)
    def delete(self, username):
        """
        Endpoint to delete an existing user from the server.

        Args:
            username (str): a user name provided from the URL.

        Returns:
            str: should return an empty string as part of the convention of rest APIs.
        """
        return ServiceClassWrapper(
            class_type=self._user_service_implementation,
            model=self._user_model
        ).delete(username=username)


class ClientController(Controller):
    """
    Client controller in order to interact with our client application.
    """
    def __init__(self, client_service_implementation, client_model):
        self._client_service_implementation = client_service_implementation
        self._client_model = client_model

    @response_decorator(code=HttpCodes.OK)
    def post(self):
        """
        Endpoint to create a client in the server.

        Returns:
            dict: a new client response to the client application.
        """
        return ServiceClassWrapper(
            class_type=self._client_service_implementation,
            model=self._client_model
        ).create(**request.json)

    @response_decorator(code=HttpCodes.OK)
    def get(self, id=None):
        """
        Endpoint to get clients from the server.

        Args:
            id (str): client ID to get.

        Returns:
            dict: an existing client response to the client application.
        """
        if id:  # get single client.
            return ServiceClassWrapper(
                class_type=self._client_service_implementation,
                model=self._client_model
            ).get_one(client_id=id)
        else:  # get all the clients.
            return ServiceClassWrapper(
                class_type=self._client_service_implementation,
                model=self._client_model
            ).get_many()

    @response_decorator(code=HttpCodes.NO_CONTENT)
    def delete(self, username):
        """
        Endpoint to delete an existing user from the server.

        Args:
            username (str): a user name provided from the URL.

        Returns:
            str: should return an empty string as part of the convention of rest APIs.
        """
        return ServiceClassWrapper(
            class_type=self._client_service_implementation,
            model=self._client_model
        ).delete(username=username)
