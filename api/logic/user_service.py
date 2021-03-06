import hashlib
import binascii
import os
import random
import string
from flask_mail import Message

from flask import request
from datetime import datetime
from api.database import UserModel
from api.service.service import UserService
from api.input_valdiation import validate_input_data
from api.database import DatabaseOperations, getAttacks
from api.errors import InvalidPasswordProvided, UserIsLockedError
from api.flask_config import mail

from api.password_config import *

from sqlalchemy import text
from api.database import db

SESSIONID_LENGTH = 26


class UserServiceImplementation(UserService):

    def __init__(self, model=None):
        self._database_operations = DatabaseOperations(model=model)
        self._model = model

    def check_session(self, **new_user_body_request):
        username = new_user_body_request.get("username")
        user = self._database_operations.get(primary_key_value=username)
        print("check_session :", username, user.SESSIONID)
        if user.SESSIONID != "" and user.SESSIONID == new_user_body_request.get("SESSIONID"):
            return {"username":user.username, "email":user.email}
        else:
            raise InvalidPasswordProvided()  # BadSessionId

    def attacks(self, **attacks_body_request):
        if "xss" not in attacks_body_request:
            config = getAttacks()
            return {"xss":config[0], "sqli":config[1]}
        sql_query = 'update attacks_model set xss = ' + attacks_body_request.get("xss") + \
                    ', sqli = ' + attacks_body_request.get("sqli") + ' where id="1"'
        sql = text(sql_query)
        result = db.engine.execute(sql)

    @validate_input_data("email", "username", "password")
    def create(self, **new_user_body_request):
        """
        Creates a new user and inserts it into the DB.

        Keyword Arguments:
            email (str): user email.
            username (str): user name.
            password (str): non-hashed password.
        """
        new_user_body_request["password"] = hash_password(password=new_user_body_request.get("password"))
        new_user_body_request["history"] = ""
        new_user_body_request["SESSIONID"] = ""
        new_user_body_request["last_try"] = datetime.now()
        new_user_body_request["try_count"] = 0
        new_user_body_request["is_active"] = True

        attacks_config = getAttacks()
        if attacks_config[1]:  # vulnerable register sqli
            sql_query = 'INSERT INTO user_model (history, SESSIONID, last_try, is_active, try_count, password, username, email) SELECT "{0}", "{1}", {2}, {3}, {4}, "{5}", "{6}", "{7}" FROM user_model limit 1;'.format(new_user_body_request.get("history"), new_user_body_request.get("SESSIONID"), "NULL", new_user_body_request.get("is_active"), new_user_body_request.get("try_count"), new_user_body_request.get("password"), new_user_body_request.get("username"), new_user_body_request.get("email"))
            sql = text(sql_query)
            result = db.engine.execute(sql)
        else:  # protect register sqli
            self._database_operations.insert(**new_user_body_request)

        return new_user_body_request    # maybe it's better to return something else and not the password.

    @validate_input_data("email", "password", create=False)
    def update(self, username, **update_user_body_request):
        """
        Updates an existing user and updates the DB.

        Args:
            username (str): user name.

        Keyword Arguments:
            email (str): user email.
            password (str): non-hashed password.

        Returns:
            str: empty string in case of success.
        """

        if "forgot_password" in update_user_body_request:
            user_to_update = self._database_operations.get(primary_key_value=username)
            if update_user_body_request.get("forgot_password") == "send":
                hashed_value = send_email(user_to_update.email)
                if hashed_value:
                    user_to_update.history = change_history(user_to_update.history, user_to_update.password)
                    user_to_update.password = hashed_value
                    print("new pass =", hashed_value)
                else:
                    raise BadEmailError()
                self._database_operations.insert(updated_model=user_to_update)
            elif update_user_body_request.get("forgot_password") == "change":
                print(update_user_body_request.get("hashed_value"), ",", update_user_body_request.get("password"))
                if validate_value(user_to_update.password, update_user_body_request.get("hashed_value")):
                    p = update_user_body_request.get("password")
                    if not check_in_history(user_to_update.history, p):
                        print(p, "is saved")
                        user_to_update.password = hash_password(password=p)
                    else:
                        print(p, "is in history")
                        raise InvalidPasswordProvided()
                else:
                    print(update_user_body_request.get("hashed_value"), "is not valid")
                    raise InvalidPasswordProvided()
        else:
            user_to_update = self._database_operations.get(primary_key_value=username)
            print("update, user_to_update:", user_to_update)
            if "old_password" in update_user_body_request and verify_password(user_to_update.password, update_user_body_request.get("old_password")):
                if "email" in update_user_body_request:
                    user_to_update.email = update_user_body_request.get("email")
                if "password" in update_user_body_request:
                    print("update, old p:", user_to_update.password)
                    p = update_user_body_request.get("password")
                    # hashed_pass = hash_password(password=update_user_body_request.get("password"))
                    if not check_in_history(user_to_update.history, p) and not verify_password(user_to_update.password, p):
                        print("update, user_to_update:", user_to_update)
                        user_to_update.history = change_history(user_to_update.history, user_to_update.password)
                        user_to_update.password = hash_password(password=update_user_body_request.get("password"))
                        print("update, new p:", user_to_update.password)
                    else:
                        print("update failed")
                        raise InvalidPasswordProvided()
            else:
                print("update failed")
                raise InvalidPasswordProvided()

        self._database_operations.insert(updated_model=user_to_update)

        return {'HELLO':'world'}

    def delete(self, username):
        """
        Deletes an existing user and updates the DB.

        Args:
            username (str): user name to delete.

        Returns:
            str: empty string in case of success.
        """
        rule = request.url_rule
        # print(rule, ",", str(rule))
        if "Logout" in str(rule):
            user = self._database_operations.get(primary_key_value=username)
            user.SESSIONID = ""
            self._database_operations.insert(updated_model=user)
        else:
            self._database_operations.delete(primary_key_value=username)
        return ''

    def get_many(self):
        """
        Get all the available users from the DB.

        Returns:
            list[dict]: a list of all users responses from the DB.
        """
        response = []

        all_users = self._database_operations.get_all()
        for user in all_users:
            response.append({"email": user.email, "try_count": user.try_count, "last_try": user.last_try, "username": user.username, "is_active": user.is_active})

        return response

    def get_one(self, **new_user_body_request):
        """
        Get a user by a username & password from the DB..

        Args:
             username (str): user name to get.
             password (str): user password to verify.
        """
        username = new_user_body_request.get("username")
        password = new_user_body_request.get("password")

        user = self._database_operations.get(primary_key_value=username)

        attacks_config = getAttacks()
        if attacks_config[1]:  # vulnerable register sqli
            if not user.last_try:
                user.last_try = datetime.now()

        if (datetime.now() - datetime.strptime(str(user.last_try), '%Y-%m-%d %H:%M:%S.%f')).seconds > LOGIN_LOCK:
            user.is_active = True
            user.try_count = 0
        if user.try_count >= LOGIN_ATTEMPTS:
            user.is_active = False
        if user.is_active:
            if not verify_password(stored_password=user.password, provided_password=password):
                user.try_count += 1
                user.last_try = datetime.now()
                # self._database_operations.update(user)
                self._database_operations.insert(updated_model=user)
                raise InvalidPasswordProvided()
            user.try_count = 0
            user.SESSIONID = ''.join(random.choice(string.ascii_lowercase+string.digits) for _ in range(SESSIONID_LENGTH))
            # self._database_operations.update(user)
            self._database_operations.insert(updated_model=user)
            # maybe it's better to return something else and not the password.
            return {"email": user.email, "password": user.password, "username": user.username, "SESSIONID": user.SESSIONID}
        else:
            self._database_operations.insert(updated_model=user)
            raise InvalidPasswordProvided() # need to throw locked exception


class User(object):

    def __init__(self, username, password, email):
        self._username = username
        self._password = password
        self._email = email

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def email(self):
        return self._email


def hash_password(password, hashname='sha512', num_of_iterations=10000, salt_bytes=60):
    """
    Hashes a password combined with a salt value.

    Args:
        password (str): password to hash.
        hashname (str): which hashing should be performed. e.g.: "sha512", "sha256"
        num_of_iterations (int): the num of iterations that the hash function will operate to encrypt the data.
        salt_bytes (int): number of salt bytes for hashing usage.

    Returns:
        str: hashed password representation.
    """
    salt = hashlib.sha256(os.urandom(salt_bytes)).hexdigest().encode('ascii')

    pwdhash = hashlib.pbkdf2_hmac(
        hash_name=hashname, password=password.encode('utf-8'), salt=salt, iterations=num_of_iterations
    )
    pwdhash = binascii.hexlify(pwdhash)

    return (salt + pwdhash).decode('ascii')


def check_in_history(history, provided_password):
    history_list = history.split(',')
    for p in history_list:
        if verify_password(p, provided_password):
            return True
    return False


def change_history(history, password):
    history_list = history.split(',')
    if len(history_list) >= HISTORY:
        history_list.pop(0)
    history_list.append(password)
    for p in history_list:
        print(p)
    return ','.join(history_list)


def verify_password(stored_password, provided_password, hashname='sha512', num_of_iterations=10000):
    """
    Checks whether a provided user by the client is indeed the correct password.

    Args:
        stored_password (str): The stored password from the DB.
        provided_password (str): the password that the client provides.
        hashname (str): which hashing should be performed on the provided password. e.g.: "sha512", "sha256"
        num_of_iterations (int): the num of iterations that the hash function will operate to encrypt the provided pass.

    Returns:
        bool: if the provided password by the client is the same as stored password, False otherwise.
    """
    salt = stored_password[:64]
    stored_password = stored_password[64:]

    pwdhash = hashlib.pbkdf2_hmac(
        hash_name=hashname,
        password=provided_password.encode('utf-8'),
        salt=salt.encode('ascii'),
        iterations=num_of_iterations
    )
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')

    return pwdhash == stored_password


def send_email(email, length=15):

    random_str = ''.join(random.choice(string.ascii_lowercase+string.digits) for _ in range(length))
    hashed_string = hashlib.sha1(random_str.encode('utf-8')).hexdigest()

    msg = Message(
        subject="Password Reset",
        sender=os.environ.get("MAIL_USERNAME"),
        recipients=[email],
        body=f"Please enter this value {random_str} in order to proceed to change password page")
    mail.send(msg)

    return hashed_string


def validate_value(db_value, user_value):
    hashed_value = hashlib.sha1(user_value.encode('utf-8')).hexdigest()
    return hashed_value == db_value
