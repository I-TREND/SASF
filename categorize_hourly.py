#!/usr/bin/env python
import os
import sys
PROJECT_NAME = 'project'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", PROJECT_NAME + ".settings")

from quirks.iterable import product,count
from app.models import Query,Engine, Search, SearchResult
from app.util import do_search, do_categorize
from random import randint
from time import sleep
import datetime
from django.utils.timezone import now


import logging
logger = logging.getLogger('__main__')

SEARCH_INTERVAL = 5
MAX_QUERIES = 30

if __name__ == '__main__':
    queries = count(MAX_QUERIES-1,-1)
    for search in Search.objects.filter(query__isnull=False, date__gt = now()-datetime.timedelta(SEARCH_INTERVAL)).order_by('-date'):
        if SearchResult.objects.filter(
            search=search, site__group=search.group, site__fresh=True, site__banned=False, site__category__isnull=True
        ).exists():
            try:
                if not do_categorize(search, queries):
                    break
            except Exception as e:
                logger.error(e)

sys.exit(0)