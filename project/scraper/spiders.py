# coding=utf-8
# Scrapy spider and spider generator based on descriptors in DB

from __future__ import with_statement
from itertools import chain
from urlparse import urlsplit

from scrapy.contrib.linkextractors.lxmlhtml import LxmlParserLinkExtractor
from scrapy.contrib.linkextractors.regex import RegexLinkExtractor
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule

from .items import ScraperItem
from .extractor import get_extractor

from app.models import SiteData, ScraperDescriptor

class BaseSpider(CrawlSpider):
    name = "Base"
    site__id = None
    extractors = None
    allowed_domains = []
    start_urls = []
    session = None
    rules = (
        Rule(RegexLinkExtractor(),callback='parse_item'),
        Rule(SgmlLinkExtractor(),callback='parse_item'),
        Rule(LxmlParserLinkExtractor(),callback='parse_item'),
    )

    def process_results(self, response, results):
        return chain(results, self.parse_item(response))

    def parse_item(self, response):
        for extractor in self.extractors:
            values = {
                'URL_PROD': response.url,
                }
            extract = {}
            for e in extractor(response):
                extract.update(e) # TODO: check relevance if overwriting
            for k,v in extract.iteritems():
                values[k] = v[0]
            name = values.get('NAME_PROD')
            if name:
                yield  ScraperItem(name=name, site=self.site__id, values=values.iteritems())

def get_spiders(site_id = None):
    name = 'site-%d'%site_id
    spiders = {}
    if site_id:
        sites = SiteData.objects.filter(id=site_id)
    else:
        sites = SiteData.objects.filter(category__symbol = 'approved')
    for site in sites:
        sds = ScraperDescriptor.objects.filter(site=site)
        if not sds.exists():
            continue
        url = site.site.url
        start_urls = list(chain((url,), [sd.url for sd in sds]))
        _, netloc, _, _, _ = urlsplit(url)
        spider_name = 'site-%d'%site.id
        extractor = get_extractor(site.id)
        if extractor is not None:
            spiders[spider_name] = type(spider_name, (BaseSpider,), dict(
                name = spider_name,
                extractors = [extractor,],
                site__id = site.id,
                allowed_domains = [netloc,],
                start_urls = start_urls,
            ))
    return spiders if name is None else spiders.get(name)
