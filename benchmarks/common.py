from redisco import models


class Event(models.Model):
    name = models.Attribute()
    location = models.Attribute()
