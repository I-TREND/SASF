from django.template import TemplateDoesNotExist

__author__ = 'pborky'

import types
from django.contrib import messages
from django.views.decorators import http
from django.http import HttpResponse
from django.conf.urls import url
from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth import get_user
from django.contrib.auth.models import User


from quirks.functional import partial

import logging
logger = logging.getLogger(__name__)

def get_group(user):
    from models import BaseGroup
    if not isinstance(user, User):
        user = get_user(user)
    try:
        return BaseGroup.objects.get(user=user).group
    except:
        return

def autoregister(*app_list):
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass


class Decorator(object):
    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
    def __call__(self, *args, **kwargs):
        return self.func.__call__(*args, **kwargs)

def view(
    pattern,
    template = None,
    form_cls = None,
    redirect_to = None,
    redirect_attr = None,
    redirect_fallback=None,
    invalid_form_msg = 'Form is not valid.',
    decorators = (),
    content_type = None,
    methods = ('get','post', 'option', 'put', 'delete', 'head'),
    **kwargs
):
    class Wrapper(Decorator):
        def __init__(self, obj):
            super(Wrapper, self).__init__(obj)

            if isinstance(obj, types.ClassType):
                obj = obj()

            permitted_methods = {}

            for method in methods:
                if hasattr(obj, method):
                    fnc = getattr(obj, method)
                    if not isinstance(fnc, types.FunctionType):
                        fnc = partial(fnc, obj)
                    permitted_methods[method.upper()] = fnc

                else:
                    # in case we have decorated function instead of class..
                    if callable(obj):
                        permitted_methods[method.upper()] = obj

            require_http_methods_decorator = http.require_http_methods(request_method_list=permitted_methods.keys())
            for key, val in  permitted_methods.items():
                setattr(self, key.lower(), val)

            self.permitted_methods = permitted_methods.keys()

            self.inner = reduce(lambda fnc, dec: dec(fnc), (require_http_methods_decorator,)+decorators, self.inner )

        @staticmethod
        def _mk_forms(*args, **kwargs):
            if isinstance(form_cls,tuple) or isinstance(form_cls, list):
                return list(f(*args, **kwargs) for f in form_cls)
            elif isinstance(form_cls, dict):
                return dict((k,f(*args, **kwargs)) for k,f in form_cls.iteritems())
            else:
                if form_cls is not None:
                    return [form_cls(*args, **kwargs),]
                else:
                    return [None,]
        @staticmethod
        def _is_valid(forms):
            if isinstance(forms,dict):
                it = forms.itervalues()
            else:
                it = forms
            return all(f.is_valid() if f is not None else True for f in it)
        def url(self):
            return url(pattern, self, kwargs, self.__name__)

        def __call__(self, *args, **kwargs):
            return self.inner(*args, **kwargs)

        def inner(self, request, *args, **kwargs):
            from django.shortcuts import render, redirect

            logger.debug('%s %s, User: %s, IP: %s' % (request.META.get('REQUEST_METHOD'),  request.get_full_path(), get_user(request), request.META.get('REMOTE_ADDR')))

            try:

                fallback = False

                if not request.method in self.permitted_methods:
                    return http.HttpResponseNotAllowed(permitted_methods=self.permitted_methods)

                if request.method in ('POST',):

                    forms = self._mk_forms(request.POST, request=request)  if request.POST else self._mk_forms(request=request)
                    ret =  self.post(request, *args, forms=forms, **kwargs)

                    if isinstance(ret, HttpResponse):
                        return ret

                    if not self._is_valid(forms):
                        if invalid_form_msg:
                            messages.error(request, invalid_form_msg)
                        if redirect_fallback:  # fallback if failed
                            return redirect(redirect_fallback, **ret)


                elif request.method in ('GET',) :

                    forms =  self._mk_forms(request.GET, request=request) if request.GET else self._mk_forms(request=request)

                    ret =  self.get(request, *args, forms=forms, **kwargs)

                    if isinstance(ret, HttpResponse):
                        return ret

                    if not self._is_valid(forms):
                        #forms =  self._mk_forms(request=request)
                        #messages.error(request, invalid_form_msg)
                        pass

                elif request.method in ('HEAD', 'OPTION', 'PUT', 'DELETE') :
                    ret =  {}  # not implemented yet
                    forms =  self._mk_forms(request=request)

                else:
                    return

            except AttributeError as e:
                raise e
                #return HttpResponseServerError()

            redirect_addr = request.GET[redirect_attr] if redirect_attr in request.GET else redirect_to

            if redirect_addr:
                context_vars = { }

                context_vars.update(kwargs)

                if isinstance(ret,dict):
                    context_vars.update(ret)

                return redirect(redirect_addr, *args, **context_vars)
            else:
                context_vars = {
                            'forms': forms,
                        }
                context_vars.update(kwargs)

                if isinstance(ret,dict):
                    context_vars.update(ret)

                try:
                    return render(request, template, context_vars, content_type=content_type)
                except TemplateDoesNotExist:
                    return HttpResponse()
    return Wrapper

def view_GET(*args, **kwargs):
    kwargs['methods'] = 'get',
    return view(*args, **kwargs)

def view_POST(*args, **kwargs):
    kwargs['methods'] = 'post',
    return view(*args, **kwargs)

def redirect(attr='next_url', fallback='/'):
    class Wrapper(Decorator):
        def __call__(self, request, *args, **kwargs):
            from django.shortcuts import redirect
            ret = super(Wrapper,self).__call__(request, *args, **kwargs)
            if attr in request.POST:
                next = request.POST.get(attr)
            else:
                next = request.GET.get(attr,fallback)
            return ret if ret else redirect(next)
    return Wrapper

def default_response(response_cls=HttpResponse):
    class Wrapper(Decorator):
        def __call__(self, request, *args, **kwargs):
            ret = super(Wrapper,self).__call__(request, *args, **kwargs)
            return ret if ret else response_cls()
    return Wrapper
