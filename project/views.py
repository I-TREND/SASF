__author__ = 'pborky'

from django.contrib import messages
from django.views.decorators import cache, http

from .helpers import redirect, default_response
from .forms import LoginForm

@http.require_http_methods(('GET','POST'))
@cache.never_cache
@redirect(attr='nexturl',fallback='/')
#@default_response()
def login(request):
    from django.contrib.auth import login,authenticate

    form = LoginForm(request.POST)
    try:
        if form.is_valid():
            user = authenticate(username=form.data.get('username'), password=form.data.get('password'))
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'User authentication was successful.')
                    return
                else:
                    messages.error(request, 'User account has been disabled.')
                    return
    except Exception:
        pass
    messages.error(request, 'User authentication was unsuccessful.')


@http.require_http_methods(('GET','POST'))
@cache.never_cache
@redirect(attr='nexturl',fallback='/')
#@default_response()
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'User deauthentication successful.')