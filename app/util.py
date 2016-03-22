
__author__ = 'pborky'

from .models import Query,Engine,SearchResult,Search,Keyword,Site,SiteAttributes, Ip, Whois, SiteData, SiteAnalytics, SiteAnalyticsDescriptor, KeyValueMapping, SiteAnalyticsValue, SiteInfo, KeyValue, KeyValueDescriptor
from quirks.iterable import product,itake
from quirks.functional import partial
from project.searches import engines,analytics,root_page_keywords
from project.addrutil import addrutil
from unidecode import unidecode
from django.contrib.auth.models import User
from project.helpers import get_group
from threading import Thread

import logging
logger = logging.getLogger(__name__)

class ThreadList:
    threads = {}
    results = {}
    @classmethod
    def thread(cls, key, target):
        def wrap():
            target()
            cls.results[key] = True
        t = Thread(target=wrap)
        t.daemon = True
        if key not in cls.threads:
            cls.threads[key] = []
        cls.threads[key].append(t)
        t.start()
    @classmethod
    def is_alive(cls, key):
        if key not in cls.threads:
            return False
        cls.threads[key] = [t for t in cls.threads[key] if t.is_alive()]
        if not cls.threads[key]:
            return False
        else:
            return True
    @classmethod
    def is_success(cls, key):
        if cls.is_alive(key):
            if key in cls.results:
                r = cls.results[key]
                del cls.results[key]
                return r
        return None

def url_depath(url):
    from urlparse import urlsplit, urlunsplit
    scheme, netloc, _, _, _ = urlsplit(url)
    return urlunsplit((scheme, netloc, '/', '', ''))

def do_categorize(search, queries=None):
    group = search.group

    user_keywords = Keyword.objects.filter(group__in=(group,))

    for sr in SearchResult.objects.filter(
        search=search,
        site__group=group,
        site__banned=False,
        site__categorized=False,
        site__fresh=True,
        site__category__isnull=True
    ):
        if sr.site.category is not None:
            continue

        keywords = []
        category = None
        site_data = sr.site
        site = site_data.site
        bare_url = site.url

        #logger.debug('Check category for result [id=%d] "%s".'%(search.id,bare_url,))

        try:
            scraped_keywords = root_page_keywords(bare_url)
            if not scraped_keywords:
                scraped_keywords = []
            for kw in user_keywords:
                try: kwrd = unidecode(kw.keyword.decode('utf-8')).lower()
                except:kwrd = kw.keyword
                if kwrd in scraped_keywords:
                    if category is None or kw.category == category:
                        category = kw.category
                        keywords.append(kw)
                        #break

            site_data.category= category
            site_data.categorized = True
            site_data.save()

            descriptor = KeyValueDescriptor.objects.filter(symbol='CATEGORY_SHOP')
            if descriptor.count() == 1:
                si = SiteInfo.objects.create(site=site_data, automatic=True)
                si.values.add(KeyValue.objects.create(descriptor=descriptor[0], value=site_data.category.symbol if site_data.category else '-' ))
                si.save()

            if keywords:
                sr.keyword.add(*keywords)
                sr.save()

            title = root_page_keywords.get_title()
            title = title[:100]

            if title and site.name != title :
                site.name= title
                site.save()
        except Exception as e:
            logger.exception(e)

        count = SiteData.objects.filter(
            banned=False,
            categorized=False,
            fresh=True,
            category__isnull=True
        ).count()

        logger.debug('Put "%s" [id=%d] (%d remaining) in category "%s" based on keywords %s.'%(bare_url, search.id, count, category if category else '', keywords))

        if queries is not None:
            if not queries.next():
                logger.debug('maximum queries reached')
                return False

    return True

def do_search(query, engine, user=None, count=20, categorize=True):
    if not isinstance(user, User) and user is not None:
        user = User.objects.get(username=user)
    if not isinstance(engine,Engine):
        engine = Engine.objects.get(symbol=engine)
    if not isinstance(query,Query):
        q = query
        query = None
    else:
        q = query.q

    if engine.symbol not in engines:
        return

    logger.debug('Invoking query "%s" using engine "%s".'%(q, engine.name))

    results = engines[engine.symbol](q=q)

    group = None
    if query:
        search = Search.objects.create(engine=engine, query=query, q=q)
        group = query.group
    else:
        search = Search.objects.create(engine=engine, q=q)
        if user:
            group = get_group(user)
    search.group = group
    search.manual = user is not None
    search.user = user
    search.save()

    logger.debug('Search id=%d.'%(search.id,))

    for res in itake(count, results):

        seq = res.get('_seq')+1
        bare_url = url_depath(res['url']) # remove path from url
        site_data = site = None
        try:
            site = Site.objects.get(url=bare_url)
            site_data = SiteData.objects.get(site=site, group=group)
        except Exception:
            pass

        if site_data:
            logger.debug('%02d. Old result [id=%d] "%s".'%(seq,search.id,res['url'],))
            # once processed in this run, we continue
            try:
                sr = SearchResult.objects.get(site=site_data, search=search)
                if sr:
                    sr.sequence += ', %s'% seq
                    sr.save()
                    continue
            except:
                pass

        fresh = False
        if not site_data:
            logger.debug('%02d. New result [id=%d] "%s".'%(seq,search.id,res['url'],))

            if not site:
                site = Site(name=res.get('title',) or '(no title found)', url=bare_url)
                site.save()

            fresh = True
            site_data = SiteData(site=site, group=group, banned=False, fresh=fresh, found=search)
            site_data.save()

        search_result = SearchResult.objects.create(search=search, sequence=seq, seq=seq, site=site_data)
        search_result.save()

    if categorize:
        ThreadList.thread(search.id, partial(do_categorize,search))

    return search

def is_categorizing(search):
    return ThreadList.is_alive(search.id)

def is_success(search):
    return ThreadList.is_success(search.id)

def do_get_analytics(site):
    if isinstance(site,SearchResult):
        site = site.site
    if isinstance(site,SiteData):
        site = site.site
    if not isinstance(site,Site):
        site = Site.objects.get(id=site)

    logger.debug('Site %s' % site.url)
    for a in SiteAnalyticsDescriptor.objects.filter(active=True):
        if a.symbol in analytics and a.active:
            logger.debug(' * acquiring data from %s' % a.url)
            data = dict(analytics[a.symbol](q=site.url))
            if not data:
                continue
            anal = SiteAnalytics.objects.create(site=site,descriptor=a)
            anal.save()
            for f in a.fields.all():
                if f.symbol not in data:
                    continue
                v = data.get(f.symbol)
                logger.debug(u'  * acquired %s: %s' % (f.name, v.replace('\n','')[:100]))
                value = SiteAnalyticsValue.objects.create(mapping=f, value=v[:500])
                value.save()
                anal.analytics.add(value)
                anal.save()

def do_get_addresses(site):
    if isinstance(site,SearchResult):
        site = site.site
    if isinstance(site,SiteData):
        site = site.site
    if not isinstance(site,Site):
        site = Site.objects.get(id=site)

    res = addrutil(site.url)

    site_attr = SiteAttributes(site=site)
    site_attr.save()

    ips = map(
        lambda ip: Ip.objects.get_or_create(**ip)[0],
        res.get('addresses',())
    )
    if ips:
        site_attr.ip.add(*ips)
        site_attr.save()
    whois = map(
        lambda whois: Whois.objects.get_or_create(**whois)[0],
        res.get('whois',())
    )
    if whois:
        site_attr.whois.add(*whois)
        site_attr.save()
