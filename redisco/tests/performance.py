#!/usr/bin/python
# -*- coding: utf-8 -*

import sys
import redis
import redisco
import unittest
from redisco import models


class PerformanceTestCase(unittest.TestCase):
    def setUp(self):
        self.client = redisco.get_client()
        self.client.flushdb()

    def tearDown(self):
        self.client.flushdb()

    @unittest.skipIf("--performance" not in sys.argv, "performance test take long time to do...")
    def test_performance(self):
        """
        performance test take long time to do, only use on travis server
        """

        REDIS = redis.Redis()

        class RediscoPost(models.Model):
            uid = models.Attribute(indexed=False)  # ID unico interno
            postid = models.Attribute(indexed=False)  # Id do provider
            text = models.Attribute(indexed=False)  # Texto / caption
            url = models.Attribute(indexed=False)  # URL post original
            media_url = models.Attribute(default=None, indexed=False)  # Link de eventual midia (video, imagem)
            provider = models.Attribute()  # Provider (Facebook, Twitter, Vimeo, Youtube, Instagram)
            post_type = models.Attribute()  # Tipo de post (video, texto, imagem)
            locale = models.Attribute(indexed=False)  # Lingua do post
            brand = models.Attribute()  # Marca
            userid = models.Attribute()  # Userid
            user_name = models.Attribute(indexed=False)  # User name
            user_avatar = models.Attribute(indexed=False)  # User Avatar
            country = models.Attribute()  # Pais de origem
            is_own_post = models.BooleanField(indexed=False)  # Post gerado pelo dono da marca?
            interactions = models.IntegerField()  # Numero de interacoes do post
            ts = models.IntegerField(indexed=False)  # Timestamp de criacao do post

        from datetime import datetime

        REDIS.flushall()

        start = datetime.now()
        for i in range(0, 10000):
            post = RediscoPost(uid=str(i),
                               postid=str(i),
                               text="text",
                               url="http",
                               provider=2,
                               post_type=1,
                               media_url="",
                               locale="pt",
                               brand=1,
                               country=None,
                               userid=str(i),
                               user_name="bla",
                               user_avatar="",
                               is_own_post=True,
                               interactions=10,
                               ts=i
                               )
            post.save(validate_fields=False)

        delta = datetime.now()-start
        print("SAVE REDISCO {}".format(delta))

        start = datetime.now()
        for i in range(0, 10000):
            RediscoPost.objects.get_by_id(i)
        delta = datetime.now()-start
        print("GET REDISCO {}".format(delta))

        start = datetime.now()
        for i in range(0, 10000):
            RediscoPost.objects.values().get_by_id(i)
        delta = datetime.now()-start
        print("GET REDISCO VALUES {}".format(delta))

        start = datetime.now()
        posts = RediscoPost.objects.filter(provider=2)
        for p in posts:
            p.uid
        delta = datetime.now()-start
        print("QUERY REDISCO {} {}".format(delta, len(posts)))

        start = datetime.now()
        posts = RediscoPost.objects.values().filter(provider=2)
        for p in posts:
            p["uid"]
        delta = datetime.now()-start
        print("QUERY REDISCO VALUES {} {}".format(delta, len(posts)))

        start = datetime.now()
        posts = RediscoPost.objects.filter(provider=2)[:]
        delta = datetime.now()-start
        print("QUERY REDISCO SLICE {} {}".format(delta, len(posts)))

        start = datetime.now()
        posts = RediscoPost.objects.values().filter(provider=2)[:]
        delta = datetime.now()-start
        print("QUERY REDISCO SLICE VALUES {} {}".format(delta, len(posts)))
