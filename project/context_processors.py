from forms import LoginForm

__author__ = 'pborky'

from models import SiteResource
from django.contrib.sites.models import get_current_site

def site_data(request):
    return {
        'site_resource': dict((s.name, s.value) for s in SiteResource.objects.all()),
        'current_site': get_current_site(request),
        }

def login_form(request):
    return {
        'login_form': LoginForm()
    }