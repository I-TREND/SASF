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
MAX_QUERIES = 1
RESULT_COUNT = 100

if __name__ == '__main__':
    for engine in Engine.objects.filter(active=True):
        queries = count(MAX_QUERIES-1,-1)
        for query in Query.objects.filter(active=True):
            if query.group not in engine.group.all():
                continue
            if Search.objects.filter(query=query, engine=engine, date__gt=now()-datetime.timedelta(SEARCH_INTERVAL)).exists():
                continue
            try:
                do_search(query, engine, count=RESULT_COUNT, categorize=False)
            except Exception as e:
                logger.error(e)

            if not queries.next():
                logger.debug('maximum queries (%d) for engine %s reached' % (MAX_QUERIES, engine.name))
                break
sys.exit(0)