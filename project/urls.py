from django.conf.urls import patterns, include, url

from django.contrib import admin
import tinymce.urls
import app.urls

from .helpers import autoregister

admin.autodiscover()

autoregister('app')
autoregister('project')

from .views import login,logout

urlpatterns = patterns('',
    url(r'^', include(app.urls), name='app'),

    url(r'^login$', login, name='login'),
    url(r'^logout$', logout, name='logout'),

    url(r'^tinymce/', include(tinymce.urls), name='tinymce'),
    url(r'^admin/', include(admin.site.urls), name='admin'),
)
