import os
import datetime


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'project.scraper.settings')

from django.utils.timezone import now
from app.models import SiteData, ProductInfo, ScraperDescriptor
from project.scraper.spiders import get_spiders

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

import logging
logger = logging.getLogger('__main__')

import random

SEARCH_INTERVAL = 1
MAX_SPIDERS = 3

if __name__ == '__main__':
    spiders = []
    sites = list(SiteData.objects.filter(category__symbol='approved'))
    random.shuffle(sites)
    for site in sites:
        if ProductInfo.objects.filter(product__page__site=site, date__gt = now()-datetime.timedelta(SEARCH_INTERVAL)).exists():
            continue
        if not ScraperDescriptor.objects.filter(site=site).exists():
            continue

        Spider = get_spiders(site.id)
        if Spider is not None:
            spiders.append(Spider())

        if len(spiders) > MAX_SPIDERS:
            break
    if spiders:
        settings = get_project_settings()
        crawler_process = CrawlerProcess(settings)
        for spider in spiders:
            crawler = crawler_process.create_crawler(name=spider.name)
            crawler.crawl(spider)
        crawler_process.start()

