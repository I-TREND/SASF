from .base import *

DEBUG = False
TEMPLATE_DEBUG = False
COMPRESS_ENABLED = True

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Uncomment to precompress files during deployment (also update Makefile)
# COMPRESS_OFFLINE = True

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.',
            'NAME': '',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }

# Memcached is better choice, if you can set it up; if not, this is a good
# alternative.
CACHES = {
    'default': {
        'BACKEND': ENV_SETTING('CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache')
    }
}

# Enable Raven if it's installed
try:
    import raven.contrib.django.raven_compat  # noqa
    INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

    # Raven will try to use SENTRY_DSN from environment if possible (eg. on
    # Heroku). If you need to set it manually, uncomment and set SENTRY_DSN
    # setting here.
    # SENTRY_DSN = ''
except ImportError:
    pass

# Enable gunicorn if it's installed
try:
    import gunicorn  # noqa
    INSTALLED_APPS += (
        'gunicorn',
    )
except ImportError:
    pass

# Enable django-compressor if it's installed
if COMPRESS_ENABLED:
    try:
        import compressor  # noqa
        INSTALLED_APPS += ('compressor',)
        STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)
    except ImportError:
        pass
