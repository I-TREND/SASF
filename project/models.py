__author__ = 'pborky'

from django.db.models import Model,CharField, ForeignKey
from django.contrib.auth.models import User, Group

from tinymce.models import HTMLField

class SiteResource(Model):
    name = CharField(max_length=100, verbose_name='Name')
    value = HTMLField(verbose_name='Value')
    def __unicode__(self):
        return u'%s' %(self.name,)
    class Meta:
        ordering = ["name"]
        verbose_name = "Site Resource"

class BaseGroup(Model):
    user = ForeignKey(User, unique=True)
    group = ForeignKey(Group)
    def __unicode__(self):
        return u'%s -> %s' %(self.user, self.group)
    class Meta:
        ordering = ["user"]
        verbose_name = "Base Group"