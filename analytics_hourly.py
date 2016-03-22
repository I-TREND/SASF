#!/usr/bin/env python
import os
import sys
PROJECT_NAME = 'project'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", PROJECT_NAME + ".settings")

from quirks.iterable import product,count
from app.models import Site,SiteAnalytics, SiteData, SiteCategory
from app.util import do_get_analytics
from random import randint
from time import sleep
from django.utils.timezone import now
import datetime

import logging
#logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

SEARCH_INTERVAL = 5
MAX_QUERIES = 5

if __name__ == '__main__':
    sites = Site.objects.filter(id__in=SiteData.objects.filter(banned=False,category__symbol='approved').values_list('site',flat=True)).distinct()
    x = count(1)
    queries = count(MAX_QUERIES-1,-1)
    for s in sites:
        info = s.url,x.next(),len(sites)
        if SiteAnalytics.objects.filter(site=s,date__gt=now()-datetime.timedelta(SEARCH_INTERVAL)).exists():
            #logger.debug('already processed: %s (%d of %d)'%info)
            continue
        else:
            logger.debug('currently processing: %s (%d of %d)'%info)
        try:
            do_get_analytics(s)
        except Exception as e:
            logger.exception(e)

        if not queries.next():
            logger.debug('maximum queries (%d) reached' % MAX_QUERIES)
            break
sys.exit(0)