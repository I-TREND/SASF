__author__ = 'pborky'

from scraping import Chain, Form, Items, MySession , KeywordSet, Values, FullPageScraping

import logging
logger = logging.getLogger(__name__)

class ScraperMetaclass(type):
    def __new__(mcs, name, bases, attrs):
        Meta = attrs.get('Meta', None)
        scraping = getattr(Meta, 'scraping', None)
        session_init = getattr(Meta, 'session_init', {})

        def _get_session(self):
            return MySession(**session_init)

        attrs.update({
            '_get_session': _get_session,
            '_scraping': scraping
        })

        new_class = super(ScraperMetaclass, mcs).__new__(mcs, name, bases, attrs)
        return new_class

class Scraper(object):
    __metaclass__ =  ScraperMetaclass
    def __init__(self):
        super(Scraper,self).__init__()
    def __call__(self, *args, **kwargs):
        sess = self._get_session()
        try:
            if 'base_url' in kwargs:
                sess.base_url = kwargs.get('base_url')
            return self._scraping(sess, *args, **kwargs)
        except Exception as e:
            logger.error(e)
        finally:
            del sess

class GoogleSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/?q=',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//div[@class="g"]//h3[@class="r"]/a',
                _next = '//a[@id="pnnext"]',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'https://www.google.com/',
            }

class BingSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//ol[@id="b_results"]/li/h2/a',
                _next = '//nav//a[@class="sb_pagN"]',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://www.bing.com/',
            }

class YahooSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="p"]'
            ),
            Items(
                _li = '//ol/li//h3/a',
                _next = '//div[@id="pg"]/a[@id="pg-next"]',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://search.yahoo.com/',
            }

class SeznamSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//div[@data-elm]/div[@class="modCont result cr"]/div/h3/a',
                _next = '//div[@class="next"]/a',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://search.seznam.cz/',
            }

class CentrumSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//ul[@class="results-list"]/li/div[@class="entry-wrap"]/h3/a',
                _next = '//ul[@class="pagination"]/li[@class="pageArrow nextPage"]/a',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://search.centrum.cz/',
            }

class AskSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/?o=1&l=dir',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//div[@id="lindm"]/div/div/div/a',
                _next = '//div[@id="paging"]/div[2]/a',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://www.ask.com/',
            }

class VidenSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//div[@id="resultframe"]/ol/li[@class="list"]/div/a',
                _next = '//div[@class="resultpages"]/span[@class="nn"]/a',
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://www.vinden.nl/',
            }


class OnetSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="qt"]'
            ),
            Items(
                _li = '//div[@class="boxResult"]/div/div/div[@class="link"]/a',
                _next = '//div[@class="boxMore"]/div[@class="moreInfo"]/a',   # '//div[@class="paginate"]/a[@class="button nextActive"]'
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://szukaj.onet.pl/',
            }


class DeltaSearch(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Items(
                _li = '//div[@class="srsa"]/a',
                _next = '//span[@class="prevnext"][last()]/a',   # '//div[@class="moreInfo"]/a'
                url = lambda a: a.get_attr('href').decode('utf-8'),
                title = lambda a: a.text().decode('utf-8'),
            )
        )
        session_init = {
            'base_url': 'http://search.delta-search.com/',
            }

# derived scrapers
class GooglePlSearch(GoogleSearch):
    class Meta(GoogleSearch.Meta):
        session_init = {
            'base_url': 'https://www.google.pl/',
            }

class GoogleCzSearch(GoogleSearch):
    class Meta(GoogleSearch.Meta):
        session_init = {
            'base_url': 'https://www.google.cz/',
            }
class GoogleFrSearch(GoogleSearch):
    class Meta(GoogleSearch.Meta):
        session_init = {
            'base_url': 'https://www.google.fr/',
            }
class GoogleNlSearch(GoogleSearch):
    class Meta(GoogleSearch.Meta):
        session_init = {
            'base_url': 'https://www.google.nl/',
            }

class BingFrSearch(BingSearch):
    class Meta(BingSearch.Meta):
        session_init = {
            'base_url': 'http://www.bing.fr',
            }
class BingNlSearch(BingSearch):
    class Meta(BingSearch.Meta):
        session_init = {
            'base_url': 'http://www.bing.nl',
            }
class YahooFrSearch(YahooSearch):
    class Meta(YahooSearch.Meta):
        session_init = {
            'base_url': 'http://fr.search.yahoo.com/',
            }
class YahooNlSearch(YahooSearch):
    class Meta(YahooSearch.Meta):
        session_init = {
            'base_url': 'http://nl.search.yahoo.com/',
            }
class AskFrSearch(AskSearch):
    class Meta(AskSearch.Meta):
        session_init = {
            'base_url': 'http://fr.ask.com/',
            }

class RootPage(Scraper):
    def __call__(self, base_url, *args, **kwargs):
        return super(RootPage, self).__call__(*args, base_url=base_url, **kwargs)
    class Meta:
        scraping = KeywordSet('/')
    def get_title(self):
        return self._scraping.get_title()

class FullPage(Scraper):
    def __call__(self, url, *args, **kwargs):
        return super(FullPage, self).__call__(*args, url=url, **kwargs)
    class Meta:
        scraping = FullPageScraping()

class AlexaAnalytics(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="q"]'
            ),
            Values(
                global_rank = '//span[@data-cat="globalRank"]/div/strong',
                pageviews_per_visitor = '//span[@data-cat="pageviews_per_visitor"]/div/strong',
                time_on_site = '//span[@data-cat="time_on_site"]/div/strong',
                links_in = '//div[@id="linksin_div"]//div[@class="box-2"]/span'
            ),
        )
        session_init = {
            'base_url': 'http://alexa.com/',
            }

class PagerankingAnalytics(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@class="urlfield"]'
            ),
            Values(
                pagerank = '//div[@id="pagerank"]//div[@class="smprbutton"]',
            ),
        )
        session_init = {
            'base_url': 'http://www.pageranking.org/',
            }
class WebsiteOutlookAnalytics(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@name="website"]'
            ),
            Values(
                daily_pageview = '//table[@class="hreview"]//tr[2]/td[2]',
                daily_adds_revenue = '//table[@class="hreview"]//tr[3]/td[2]',
                rating = '//table[@class="hreview"]//tr[4]/td[2]',
                summary = '//div[@class="wid"]',
            ),
        )
        session_init = {
            'base_url': 'http://www.websiteoutlook.com/',
            }
class WebTrafficSpyAnalytics(Scraper):
    class Meta:
        scraping = Chain(
            Form('/',
                q = '//input[@id="q"]'
            ),
            Values(
                monthly_users = '//table[@class="widget"]//tr[2]/td[2]',
                monthly_pageviews = '//table[@class="widget"]//tr[2]/td[3]',
                summary = '//div[@id="content"]/p',
            ),
        )
        session_init = {
            'base_url': 'http://websitetrafficspy.com/',
            }



engines = {
    "GOOG": GoogleSearch(),
    "GOOGPL": GooglePlSearch(),
    "GOOGNL": GoogleNlSearch(),
    "GOOGCZ": GoogleCzSearch(),
    "GOOGFR": GoogleFrSearch(),
    "SEZCZ": SeznamSearch(),
    "CENTRUM": CentrumSearch(),
    "YAHOO": YahooSearch(),
    "YAHOOFR": YahooFrSearch(),
    "YAHOONL": YahooNlSearch(),
    "BING": BingSearch(),
    "BINGFR": BingFrSearch(),
    "BINGNL": BingNlSearch(),
    "ASK": AskSearch(),
    "ASKFR": AskFrSearch(),
    "VIDEN": VidenSearch(),
    "ONETPL": OnetSearch(),
    "DELTA": DeltaSearch(),
}
analytics = {
    'Alexa': AlexaAnalytics(),
    'TrafficSpy': WebTrafficSpyAnalytics(),
    'WebsiteOut': WebsiteOutlookAnalytics(),
    'PageRankin': PagerankingAnalytics(),
}

root_page_keywords = RootPage()
full_html_page = FullPage()

