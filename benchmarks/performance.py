
#!/usr/bin/python
# -*- coding: utf-8 -*
import redis
import rom
import time
from redisco import models

REDIS = redis.Redis()


class Post(rom.Model):
    uid = rom.String(index=True, unique=True) # ID unico interno
    postid = rom.String() # Id do provider
    text = rom.String() # Texto / caption
    url = rom.String() # URL post original
    media_url = rom.String(default=None) # Link de eventual midia (video, imagem)
    provider = rom.Integer(index=True) # Provider (Facebook, Twitter, Vimeo, Youtube, Instagram)
    post_type = rom.Integer(index=True) # Tipo de post (video, texto, imagem)
    locale = rom.String()  # Lingua do post
    brand = rom.Integer(index=True) # Marca
    userid = rom.String(index=True) # Userid
    user_name = rom.String() # User name
    user_avatar = rom.String() # User Avatar
    country = rom.Integer(index=True, required=False) # Pais de origem
    is_own_post = rom.Boolean(index=True) # Post gerado pelo dono da marca?
    interactions = rom.Integer(index=True, default=0) # Numero de interacoes do post
    ts = rom.Integer(index=True) # Timestamp de criacao do post


class RediscoPost(models.Model):
    uid = models.Attribute(indexed=False) # ID unico interno
    postid = models.Attribute(indexed=False) # Id do provider
    text = models.Attribute(indexed=False) # Texto / caption
    url = models.Attribute(indexed=False) # URL post original
    media_url = models.Attribute(default=None, indexed=False) # Link de eventual midia (video, imagem)
    provider = models.Attribute() # Provider (Facebook, Twitter, Vimeo, Youtube, Instagram)
    post_type = models.Attribute() # Tipo de post (video, texto, imagem)
    locale = models.Attribute(indexed=False)  # Lingua do post
    brand = models.Attribute() # Marca
    userid = models.Attribute() # Userid
    user_name = models.Attribute(indexed=False) # User name
    user_avatar = models.Attribute(indexed=False) # User Avatar
    country = models.Attribute() # Pais de origem
    is_own_post = models.BooleanField(indexed=False) # Post gerado pelo dono da marca?
    interactions = models.IntegerField() # Numero de interacoes do post
    ts = models.IntegerField(indexed=False) # Timestamp de criacao do post

    class Meta:
        pickle = True

from datetime import datetime
# REDIS.flushall()

# start = datetime.now()
# for i in range(0, 10000):
#     post = Post(uid = i,
#             postid = i,
#             text = "text",
#             url = "http",
#             provider = 2,
#             post_type = 1,
#             media_url = "",
#             locale = "pt",
#             brand = 1,
#             country = None,
#             userid = i,
#             user_name = "bla",
#             user_avatar = "",
#             is_own_post = True,
#             interactions = 10,
#             ts = i
#         )
#     post.save()
# delta = datetime.now()-start
# print "SAVE ROM", delta

# rom.session.commit(all=True, full=True)

# start = datetime.now()
# for i in range(0, 10000):
#     Post.get(i)
# delta = datetime.now()-start
# print "GET ROM", delta

# rom.session.commit(all=True, full=True)

# start = datetime.now()
# Post.query.filter(provider=2).execute()
# delta = datetime.now()-start
# print "QUERY ROM", delta

# print
# print

# REDIS.flushall()
# import cPickle

# start = datetime.now()
# for i in range(0, 10000):
#     post = RediscoPost(uid = str(i),
#             postid = str(i),
#             text = "text",
#             url = "http",
#             provider = 2,
#             post_type = 1,
#             media_url = "",
#             locale = "pt",
#             brand = 1,
#             country = None,
#             userid = str(i),
#             user_name = "bla",
#             user_avatar = "",
#             is_own_post = True,
#             interactions = 10,
#             ts = i
#         )
#     REDIS.set(i, cPickle.dumps(post))
# delta = datetime.now()-start
# print  "PICKLE", delta

# start = datetime.now()
# for i in range(0, 10000):
#     cPickle.loads(REDIS.get(i))
# delta = datetime.now()-start
# print  "UNPICKLE", delta

# start = datetime.now()
# pickleds = REDIS.mget(range(0, 10000))
# for pickled in pickleds:
#     cPickle.loads(pickled)
# delta = datetime.now()-start
# print  "MULTI UNPICKLE", delta


# print
# print

REDIS.flushall()

start = datetime.now()
for i in range(0, 10000):
    post = RediscoPost(uid = str(i),
            postid = str(i),
            text = "text",
            url = "http",
            provider = 2,
            post_type = 1,
            media_url = "",
            locale = "pt",
            brand = 1,
            country = None,
            userid = str(i),
            user_name = "bla",
            user_avatar = "",
            is_own_post = True,
            interactions = 10,
            ts = i
        )
    post.save(validate_fields=False)

delta = datetime.now()-start
print "SAVE REDISCO", delta

start = datetime.now()
for i in range(0, 10000):
    RediscoPost.objects.get_by_id(i)
delta = datetime.now()-start
print "GET REDISCO", delta

start = datetime.now()
posts = RediscoPost.objects.filter(provider=2)
for p in posts:
    p.uid
delta = datetime.now()-start
print "QUERY REDISCO", delta, len(posts)

start = datetime.now()
posts = RediscoPost.objects.filter(provider=2)[:]
delta = datetime.now()-start
print "QUERY REDISCO SLICE", delta, len(posts)
