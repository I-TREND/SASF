from itertools import count
import os
import datetime


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from django.utils.timezone import now
from django.core.files import File
from app.models import SiteData, PrintScreen
from project.scraping import screen_shot

import logging
logger = logging.getLogger('__main__')

import random
import tempfile

MAX_SCREENSHOTS = 4
SCREENSHOT_INTERVAL = 5
SCREENSHOT_WIDTH = 1280
SCREENSHOT_HEIGHT = 1024

fd,TMP_FILE = tempfile.mkstemp(suffix='.png')
os.close(fd) ; os.chmod(TMP_FILE, 0666)

try:
    if __name__ == '__main__':
        sites = list(SiteData.objects.filter(category__symbol='approved'))
        random.shuffle(sites)
        cnt = count(MAX_SCREENSHOTS, -1)
        for site in sites:
            if PrintScreen.objects.filter(site=site, date__gt = now()-datetime.timedelta(SCREENSHOT_INTERVAL)).exists():
                continue
            if not cnt.next():
                break
            try:
                logger.debug('processing site %s' % site.site.url)


                screen_shot(site.site.url, TMP_FILE, SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT)

                with open(TMP_FILE) as f:

                    ps = PrintScreen()
                    ps.site= site
                    ps.save()

                    ps.image.save('%d_%s.png' % (site.id, ps.date.strftime('%Y%m%d%H%M%S')), File(f))
                    ps.save()

                logger.debug('saved file %s' % ps.image.path)
            except Exception as e:
                logger.error(e)

finally:
    os.remove(TMP_FILE)



