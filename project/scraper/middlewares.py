from w3lib.encoding import http_content_type_encoding
from scrapy.http import Request, FormRequest, HtmlResponse
from dryscrape import Session

import time

import logging
from webkit_scraper.driver import ConnectionError

logger = logging.getLogger(__name__)

DISCOVERY_PATH = '/tmp/webkit_service/18811'
SERVICE_NAME = 'WEBKIT'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/28.0.1500.71 Chrome/28.0.1500.71 '
DEFAULT_REQUEST_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

class WebkitSession(Session):
    discovery = None
    def __init__(self, proxy=None, user_agent=DEFAULT_USER_AGENT, headers=DEFAULT_REQUEST_HEADERS, *args, **kwargs):
        kwargs.setdefault('driver', self.get_driver())
        super(WebkitSession, self).__init__(*args, **kwargs)
        headers.setdefault('User-Agent', user_agent)
        for k,v in headers.iteritems():
            self.driver.set_header(k.lower(), ''.join(v))
        self.driver.set_attribute('plugins_enabled', False)
        self.driver.set_attribute('auto_load_images', False)
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
        retry = 5
        for i in range(5):
            try:
                from webkit_scraper.driver import Discovery
                if cls.discovery is None:
                    cls.discovery = Discovery(path=DISCOVERY_PATH)
                return cls.discovery.driver(SERVICE_NAME)
            except Exception as e:
                logger.error('Cannot create driver instance. Retry after %d seconds..' % retry)
                time.sleep(retry)
                retry *= 6
        raise ValueError('Cannot create driver instance.')


class WebkitDownloader( object ):

    def process_request_unsafe(self, request, spider ):
        spider.session.visit(request.url)
        spider.session.wait()

        body = spider.session.body()
        headers = spider.session.headers()
        headers = dict((str(k),headers[k]) for k in headers)

        encoding = http_content_type_encoding(headers.get("Content-Type"))
        if encoding is None:
            encoding = http_content_type_encoding(body)

        if encoding is None:
            encoding = 'utf-8'

        if body is None:
            return

        return HtmlResponse( spider.session.url(), body=body, encoding=encoding, headers=dict((str(k),headers[k]) for k in headers) )

    def construct_session(self, request, spider):
        if spider.session:
            try:
                _ = spider.session.url
            except ConnectionError:
                spider.session = None
            except AttributeError:
                spider.session = None

        if not spider.session or not hasattr(spider.session,'visit'):
            spider.session = WebkitSession(headers=request.headers)


    def process_request( self, request, spider ):
        if type(request) is not FormRequest:
            self.construct_session(request, spider)
            try:
                return self.process_request_unsafe(request, spider)
            except (ConnectionError,EOFError,AttributeError):
                self.construct_session(request, spider)
                return self.process_request_unsafe(request, spider)
            except:
                raise