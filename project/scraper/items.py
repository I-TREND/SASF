# coding=utf-8
# Items and items pipeline for insertion in django DB
from django.db import DatabaseError

from scrapy.exceptions import DropItem
from scrapy.item import Item, Field
from django.utils.timezone import now

import datetime
from app.models import KeyValueDescriptor, KeyValue, ProductInfo, SiteData, Page, Product

import logging
logger = logging.getLogger(__name__)


SEARCH_INTERVAL = 5

class ScraperItem(Item):
    # define the fields for your item here like:
    name = Field()
    site = Field()
    values = Field()

class DjangoDBWriterPipeline(object):

    def __init__(self):
        self.file = open('items.jl', 'wb')

    def process_item(self, item, spider):
        if type(item) is ScraperItem:
            try:
                name = item['name']

                site = SiteData.objects.filter(id=item['site'])
                if not site.exists():
                    raise DropItem('Site not present in database.')
                site = site[0]

                values = dict(item['values'])
                chem = values.get('CHEM_NAME_PROD')
                url = values.get('URL_PROD')

                if not name:
                    raise DropItem('Missing name or too low number of extracted values.')

                pg,_ = Page.objects.get_or_create(site=site, name=name)
                pr,_ = Product.objects.get_or_create(page=pg, group=site.group)

                if ProductInfo.objects.filter(product=pr, date__gt = now()-datetime.timedelta(minutes=1)).exists():
                    raise DropItem('Value already processed (duplicate).')

                pi = ProductInfo.objects.create(product=pr)

                pg.url = url
                pr.chem = chem

                for k,v in values.iteritems():
                    d = KeyValueDescriptor.objects.get(symbol=k)
                    kv = KeyValue.objects.create(descriptor=d, value=v)
                    pi.values.add(kv)

                pg.save()
                pr.save()
                pi.save()
            except DatabaseError:
                from django.db import transaction
                transaction.rollback()
        return item