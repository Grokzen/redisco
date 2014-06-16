# -*- coding: utf-8 -*-

from redis import StrictRedis

# Uncomment if cluster mode should be enabled
# from rediscluster.rediscluster import RedisCluster


startup_nodes = [
    {"host": "127.0.0.1", "port": "7000"}
]


class Client(object):
    def __init__(self, **kwargs):
        self.connection_settings = kwargs or {'host': 'localhost',
                                              'port': 6379, 'db': 0,
                                              'decode_responses': True}

    def redis(self):
        return StrictRedis(**self.connection_settings)
        # Uncomment if cluster mode should be enabled
        # return RedisCluster(startup_nodes=startup_nodes, max_connections=32, socket_timeout=0.1, decode_responses=True)

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
