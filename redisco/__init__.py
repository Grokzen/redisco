# -*- coding: utf-8 -*-

import redis

# Fix a bug in redis-py when using it for python3 and withouth hiredis
from redis import connection
connection.DefaultParser.encoding = "UTF-8"

# Fix a bug in redis-py when using hiredis with python3
if connection.DefaultParser.__name__ == "HiredisParser":
    orig_read_response = connection.DefaultParser.read_response

    def read_response_patched(self):
        response = orig_read_response(self)

        if isinstance(response, bytes) and self.encoding:
            response = response.decode(self.encoding)
        if isinstance(response, list) and self.encoding:
            out = []
            for item in response:
                if isinstance(item, list):
                    # We got nested list, decode sub-list
                    out.append([i.decode(self.encoding) if isinstance(i, bytes) else i for i in item])
                elif isinstance(item, bytes):
                    out.append(item.decode(self.encoding))
                else:
                    out.append(item)
            response = out
        return response

    # Monkey patch the original function with the patched one
    connection.DefaultParser.read_response = read_response_patched


class Client(object):
    def __init__(self, **kwargs):
        self.connection_settings = kwargs or {'host': 'localhost',
                                              'port': 6379, 'db': 0}

    def redis(self):
        return redis.Redis(**self.connection_settings)

    def update(self, d):
        self.connection_settings.update(d)


def connection_setup(**kwargs):
    global connection, client
    if client:
        client.update(kwargs)
    else:
        client = Client(**kwargs)
    connection = client.redis()


def get_client():
    global connection
    return connection

client = Client()
connection = client.redis()
default_expire_time = 60

__all__ = ['connection_setup', 'get_client']
