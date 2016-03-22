
import time
import logging

from w3lib.encoding import http_content_type_encoding
from HTMLParser import HTMLParser

from scrapely import HtmlPage
from dryscrape import Session
from quirks.iterable import isiterable, chain, imap
from quirks.functional import maybe, combinator
from unidecode import unidecode

logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/28.0.1500.71 Chrome/28.0.1500.71 '
ACCEPT_LANG = 'en-US,en;q=0.8'
ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

#DISCOVERY_HOST = 'localhost'
#DISCOVERY_PORT = 18811
DISCOVERY_PATH = '/tmp/webkit_service/18811'
SERVICE_NAME = 'WEBKIT'

class HtmlTagStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []
        self.skip = {
            'script': 0,
            'style': 0,
        }
    def handle_starttag(self, tag, attrs):
        if tag in self.skip.keys():
            self.skip[tag] += 1
    def handle_endtag(self, tag):
        if tag in self.skip.keys():
            self.skip[tag] -= 1
    def handle_data(self, d):
        if not any(self.skip.values()):
            self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
    @classmethod
    def strip(cls, html):
        s = cls()
        s.feed(html)
        return s.get_data()

class Scraping(object):
    pass

class FullPageScraping(Scraping):
    def __init__(self, *args, **kwargs):
        self.session = None
    def __call__(self, session, url, *args, **kwargs):
        self.session = session
        session.visit(url)
        session.wait()

        body = session.body()
        headers = session.headers()
        headers = dict((k,headers[k]) for k in headers)
        content_type_header = headers.get("Content-Type")
        encoding = http_content_type_encoding(content_type_header)

        return HtmlPage(session.url(), headers=headers, body=body, encoding=encoding)

class KeywordSet(Scraping):
    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.session = None
    def __call__(self, session, *args, **kwargs):
        self.session = session
        session.visit(self.path)
        session.wait()
        full_page = session.body()
        full_page = unidecode(full_page if isinstance(full_page, unicode) else full_page.decode('utf-8'))
        return  set(s.strip(' .,?!') for s in HtmlTagStripper.strip(full_page).lower().split())
    def get_title(self):
        return self.session.eval_script('document.title') if self.session else None

class Form(Scraping):
    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.fields =  kwargs # xpaths of the fields
    def __call__(self, session, *args, **kwargs):
        session.clear_cookies()
        session.visit(self.path)
        session.wait()
        logger.debug('visited "%s"'%session.url() )
        forms = []
        for k,v in self.fields.iteritems() :
            node = session.at_xpath(v)
            val = kwargs.get(k)
            node.set(val if val else '')
            form = node.form()
            if form not in forms and form is not None:
                forms.append(form)
        if  not forms:
            logger.error('Cannot submit form.')
            return

        def submit(delay=0):
            forms[0].submit()
            #TODO: remove delays and fix problem with webkit
            if delay:time.sleep(delay)
            session.wait()
            logger.debug('submited %s' % forms[0])
            logger.debug('url %s' % session.url())
            if delay:time.sleep(delay)
            return True

        if not submit():
            logger.debug('retrying submit')
            submit(0.5)

class Items(Scraping):
    def __init__(self, *args, **kwargs):
        self.fields =  kwargs
    def __call__(self, session, *args, **kwargs):
        return PageIterator(session, **self.fields)

class Values(Scraping):
    def __init__(self, *args, **kwargs):
        self.fields =  kwargs
    def __call__(self, session, *args, **kwargs):
        data = {}
        for k,v in self.fields.iteritems():
            val = session.xpath(v)
            if val:
                try:
                    data[k] = '\n'.join(v.text() for v in val)
                except TypeError:
                    logger.error('No text found.')
        return data.iteritems()

class PageIterator(object):
    def __init__(self,  session, **fields):
        self.session = session
        self.next = fields.pop('_next', None)
        self.li = fields.pop('_li', None)
        self.__url = None
        #self.fields = fields # xpaths of the fields applied to li nodes
        self.fields = dict( (k,maybe(f)) if callable(f) else f for k,f in  fields.items() )
    def _url(self,session):
        if self.__url is None:
            try:
                self.__url =  session.url()
            except Exception as e:
                logger.exception(e)
        return self.__url
    @staticmethod
    def _value(node, selector):
        if callable(selector):
            return selector(node)
        elif isinstance(selector,(list,tuple)):
            for sel in selector:
                result = PageIterator._value(node, sel)
                if result: return result
            return None
        else:
            xpath_or_css = maybe(node.at_xpath, node.at_css)
            return xpath_or_css(selector)
    @staticmethod
    def _values(node, selector):
        if callable(selector):
            result = (selector(node))
            return result if isiterable(result) else [result]
        elif isinstance(selector,(list,tuple)):
            for sel in selector:
                result = PageIterator._values(node, sel)
                if result: return result
            return []
        else:
            xpath_or_css = maybe(node.xpath, node.css)
            return xpath_or_css(selector)
    @staticmethod
    def _mix(d, name, value):
        d[name] = value() if callable(value) else value
        return d
    def __iter__(self):
        from quirks.iterable import count
        from urlparse import urljoin
        seq = count()
        while True:
            current_url = self.session.url()
            absolute_url = lambda url: urljoin(current_url, url)
            process_values = combinator(
                lambda  (key, value): (key, absolute_url(value) if key == 'url' else value),
            )
            results = self._values(self.session,self.li)
            if not results:
                results = []
            for result in results :
                yield dict( chain(
                    imap(process_values, ( (key,self._value(result, selector)) for key,selector in self.fields.iteritems() )),
                    ( ('_seq', seq.next()), ('_url', self._url(self.session)) )
                ) )
            if not self.next:
                return
            next = self._value(self.session,self.next)
            if not next:
                return
            self.__url = None
            next.click()
            time.sleep(0.5)
            self.session.wait()
            logger.debug('visited "%s"'%self.session.url() )

class Chain(object):
    def __init__(self, *scrapings):
        self.scrapings = scrapings
    def __call__(self, session, *args, **kwargs):
        from itertools import ifilter, chain
        # lazily evaluate chained scrapings, filter out None results
        return chain.from_iterable(
            ifilter(None,
                (scrap(session, *args, **kwargs) for scrap in self.scrapings)
            )
        )

class MySession(Session):
    discovery = None
    def __init__(self, proxy=None, *args, **kwargs):
        kwargs.setdefault('driver', self.get_driver())

        plugins_enabled = kwargs.pop('plugins_enabled',False)
        auto_load_images = kwargs.pop('auto_load_images', False)
        user_agent = kwargs.pop('user-agent', USER_AGENT)
        accept_language = kwargs.pop('accept-language', ACCEPT_LANG)
        accept = kwargs.pop('accept', ACCEPT)

        super(MySession, self).__init__(*args, **kwargs)
        self.driver.set_header('user-agent',user_agent)
        self.driver.set_header('accept-language', accept_language)
        self.driver.set_header('accept', accept)
        self.driver.set_attribute('plugins_enabled', plugins_enabled)
        self.driver.set_attribute('auto_load_images', auto_load_images)
        self.set_error_tolerant(True)
        self.clear_cookies()
        if proxy: self.set_proxy(*proxy) # tuple (host,port)
    def __del__(self):
        try:
            del self.driver
        except Exception as e:
            logger.error(e)
    @classmethod
    def get_driver(cls):
        for i in range(3):
            try:
                from webkit_scraper.driver import Discovery
                if cls.discovery is None:
                    cls.discovery = Discovery(path=DISCOVERY_PATH)
                return cls.discovery.driver(SERVICE_NAME)
            except Exception as e:
                logger.exception('Cannot create driver instance.')
                time.sleep(0.5)
        raise ValueError('Cannot create driver instance.')


def screen_shot(base_url, file_name, width, height):
    sess = MySession(base_url=base_url, auto_load_images=True)
    sess.visit('/')
    sess.wait()
    sess.driver.render(file_name, width, height)