# Scrapy settings for scraper project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'scraper'

SPIDER_MODULES = ['project.scraper.spiders']
NEWSPIDER_MODULE = 'project.scraper.spiders'
DOWNLOADER_MIDDLEWARES = {
    'scrapy.contrib.downloadermiddleware.httpcompression.HttpCompressionMiddleware':None,
    'scrapy.contrib.downloadermiddleware.chunked.ChunkedTransferMiddleware':None,
    'project.scraper.WebkitDownloader': 553,
    }

ITEM_PIPELINES = {
    'project.scraper.DjangoDBWriterPipeline': 300,
    }

EXTENSIONS_BASE = {
    'scrapy.contrib.throttle.AutoThrottle': 0,
    'scrapy.contrib.corestats.CoreStats': 0,
    'scrapy.contrib.spiderstate.SpiderState': 0,
    'scrapy.contrib.feedexport.FeedExporter': 0,
    'scrapy.contrib.memusage.MemoryUsage': 0,
    'scrapy.contrib.logstats.LogStats': 0,
    'scrapy.contrib.memdebug.MemoryDebugger': 0,
    'scrapy.contrib.closespider.CloseSpider': 0
}

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/28.0.1500.71 Chrome/28.0.1500.71 '
DEFAULT_REQUEST_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

CONCURRENT_ITEMS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
RANDOMIZE_DOWNLOAD_DELAY =  True

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scraper (+http://www.yourdomain.com)'
