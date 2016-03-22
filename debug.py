#!/usr/bin/env python
import os
PROJECT_NAME = 'project'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", PROJECT_NAME + ".settings")

from quirks.iterable import product
from app.models import Query,Engine, SearchResult
from app.util import do_search
from random import randint
from time import sleep
from itertools import count

import logging
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    import sys
    search = do_search(sys.argv[1], sys.argv[2], sys.argv[3], )
    seq = count(1)
    print '\n'.join('%2d. %s' % (seq.next(), s.site) for s in SearchResult.objects.filter(search=search).order_by('sequence'))
