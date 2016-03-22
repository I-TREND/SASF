from itertools import count

import os
import datetime


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from django.utils.timezone import now
from app.models import SiteData, ProductInfo, ScraperDescriptor, ScraperTemplate
from project.scraper.extractor import annotate

import logging
logger = logging.getLogger('__main__')

if __name__ == '__main__':
    for site in SiteData.objects.filter(category__symbol='approved'):
        sds = ScraperDescriptor.objects.filter(site=site)
        if not sds.exists():
            continue
        sts = ScraperTemplate.objects.filter(descriptor__in=sds, active=True, annotated=False)
        if not sts.exists():
            continue
        if all(ScraperTemplate.objects.filter(descriptor__in=sds, active=True, annotated=True, original=st).exists() for st in sts):
            continue

        for sd in sds:
            annotate(sd.id)

