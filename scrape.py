# coding=utf-8
from __future__ import with_statement
from itertools import chain

import os
import sys

PROJECT_NAME = 'project'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", PROJECT_NAME + ".settings")

from app.models import KeyValueDescriptor, KeyValue, ProductInfo, SiteData, Page, Product, DescriptorType, ScraperDescriptor
from django.contrib.auth.models import Group

from scrapely import Scraper
#with  open('myscraper.json') as f:
#    s = Scraper.fromfile(f)
#d = s.scrape('http://mefedronprodej.webnode.cz/produkty-1/')


import sys, os, re, cmd, shlex, json, optparse, json, urllib, pprint
from cStringIO import StringIO

from scrapely.htmlpage import HtmlPage, page_to_dict, url_to_page
from scrapely.template import TemplateMaker, best_match, FragmentAlreadyAnnotated
from scrapely.extraction import InstanceBasedLearningExtractor
from scrapely.descriptor import FieldDescriptor,ItemDescriptor
from scrapely.extractors import text, html, image_url, extract_number , extract_price


def pure_text(*args, **kwargs):
    def fnc(txt):
        txt = text(txt)
        return txt.strip()
    return fnc

def price(value, *args, **kwargs):
    import re
    _PRICE = re.compile(r'([A-Z]{3}|$€|[A-Z]\w+)?\s*([\d\s]+(?:[.,]\d+)?)\s*([A-Z]{3}|$€|[A-Z]\w+)?', re.U)
    prc = _PRICE.findall(value)
    currency = prc and prc[0][0] or prc[0][2]
    prefix = bool(prc and prc[0][0])
    def fnc(txt):
        _pt = r'(?P<currency>%s)\s*(?P<price>[\d\s]+(?:[.,]\d+)?)' if prefix else r'(?P<price>[\d\s]+(?:[.,]\d+)?)\s*(?P<currency>%s)'
        _pt = re.compile(_pt%currency, re.U)
        r = _pt.findall(txt)
        return r[0] if r else None
    return fnc

def pure_price(*args, **kwargs):
    fnc = price(*args, **kwargs)
    def fnc2(txt):
        match = fnc(txt)
        if not match:
            return None
        prc,_ = match
        return prc
    return fnc2

def pure_currency(*args, **kwargs):
    fnc = price(*args, **kwargs)
    def fnc2(txt):
        match = fnc(txt)
        if not match:
            return None
        _,cur = match
        return cur
    return fnc2

def measure(value, *args, **kwargs):
    import re
    _PRICE = re.compile(r'([A-Z]{3}|$€|[MGTEmunpd]?[a-zA-Z]+)?\s*([\d\s]+(?:[.,]\d+)?)\s*([A-Z]{3}|$€|[MGTEmunpd]?[a-zA-Z]+)?', re.U)
    prc = _PRICE.findall(value)
    currency = prc and prc[0][0] or prc[0][2]
    prefix = bool(prc and prc[0][0])
    def fnc(txt):
        pt = r'(?P<measure>%s)\s*(?P<qty>\d+(?:\.\d+)?)' if prefix else r'(?P<qty>\d+(?:\.\d+)?)\s*(?P<measure>%s)'
        pt = re.compile(pt%currency, re.U)
        r = pt.findall(txt)
        return r[0] if r else None
    return fnc

def pure_qty(*args, **kwargs):
    fnc = measure(*args, **kwargs)
    def fnc2(txt):
        match = fnc(txt)
        if not match:
            return None
        qty,_ = match
        return qty
    return fnc2

def pure_unit(*args, **kwargs):
    fnc = measure(*args, **kwargs)
    def fnc2(txt):
        match = fnc(txt)
        if not match:
            return None
        _,uni = match
        return uni
    return fnc2


def save_templates(fn, site_id, templates):
    tpls = {}
    for i,p in ((x.page_id, page_to_dict(x)) for x in templates):
        if i not in tpls:
            tpls[i] = []
        tpls[i].append(p)

    try:
        with open(fn, 'r') as f:
            obj = json.load(f)
    except IOError:
        obj = {
            'templates': [],
            'sites': {},
            }

    if 'sites' not in obj or not obj['sites'] or not isinstance(obj['sites'], dict):
        obj['sites'] = {}
    obj['sites'].update( [( site_id, list(tpls.keys()) )] )

    for i,p in ( (x['page_id'],x) for x in obj['templates'] ):
        if i not in tpls:
            tpls[i] = []
        tpls[i].append(p)

    obj['templates'] = list(chain(*tpls.values()))

    with open(fn, 'w') as f:
        json.dump(obj, f)

def load_templates(fn, site_id):
    try:
        with open(fn, 'r') as f:
            obj = json.load(f)
    except IOError:
        return list()

    tmpl_ids = obj['sites'].get(unicode(site_id))
    if not tmpl_ids:
        return list()
    return list( HtmlPage(**x) for x in obj['templates'] if x['page_id'] in tmpl_ids )


def annotate(url, site_id, items):
    t = url_to_page(url)
    tms = [TemplateMaker(t)]

    for n, s in items:

        func = best_match(s)
        sel = tms[-1].select(func)
        print 'ATTRIBUTE: %s' % n
        for i in sel:
            print u'[%d] %s' % (i, tms[-1].selected_data(i))
        if len(sel) == 1:
            row = sel[0]
        else:
            row = raw_input('? ')
            try:
                row = int(row)
            except ValueError:
                row = sel[0]
                #row = int(raw_input('? ')) #rows.pop(0)
        print 'SELECTED: %d' % row
        print ''
        annotated = False
        for tm in tms:
            try:
                if tm.annotate_fragment(row, n):
                    annotated = True
                    break
            except FragmentAlreadyAnnotated:
                pass
        if not annotated:
            tms.append(TemplateMaker(t))
            tms[-1].annotate_fragment(row, n)

    save_templates('scraper.json', site_id, (tm.get_template() for tm in tms))
    return [tm.get_template() for tm in tms]

types = {
    'TEXT': pure_text,
    'PRICE': pure_price,
    'CURRENCY': pure_currency,
    'QTY': pure_qty,
    'UNIT': pure_unit,
}

if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    url = 'http://www.rc-chem.eu/'  # http://mefedronprodej.webnode.cz/.

group = Group.objects.get(id=1)
site = SiteData.objects.get(site__url=url,group=group)
sds = ScraperDescriptor.objects.filter(site=site)

tmpls = []

if sds.exists():
    for s in sds:
        items = s.items.filter(descriptor__target__symbol='ProductInfo')
        idesc = ItemDescriptor('', '', [ FieldDescriptor(i.descriptor.symbol, i.descriptor.desc, extractor=types[i.descriptor.typ.symbol](i.value))  for i in items ] )
        ts = load_templates('scraper.json', 'scraper-%d'%s.id)
        if not ts:
            ts = annotate(s.url, 'scraper-%d'%s.id, [ (i.descriptor.symbol, i.value)  for i in items ])
        tmpls += [ (t, idesc) for t in ts ]
else:
    url = u'http://www.rc-chem.eu/produkty/thio-crystal'
    items = [
        (u'NAME_PROD',u'THIO', '', None),
        (u'CHEM_NAME_PROD',u'2-(methylamino)', '', None),
        (u'MIN_PRICE_PROD',u'400 CZK', '', None),
        (u'MAX_PRICE_PROD',u'25200 CZK', '', None),
        (u'CURRENCY_PROD',u'400 CZK', '', None),
        (u'MIN_QANT_PROD',u'1 g', '', None),
        (u'MAX_QANT_PROD',u'250 g', '', None),
        (u'MEASURE_PROD',u'1 g', '', None),
        ]

    items = list(
        map(
            lambda (n,s,desc): (n,s,u'%s'%(desc.name,), types[desc.typ.symbol]),
            ((n,s,KeyValueDescriptor.objects.get(symbol = n))  for n,s,_,_ in items if KeyValueDescriptor.objects.filter(symbol = n).exists() )
        )
    )
    idesc = ItemDescriptor('', '', [ FieldDescriptor(n, desc, extractor=fnc(s))  for n,s,desc,fnc in items ] )
    ts = load_templates('scraper.json', 'site-%d'%site.id)
    if not ts:
        ts = annotate(url, 'site-%d'%site.id, [ (n,s)  for n,s,_,_ in items ])
    tmpls += [ (tm, idesc) for tm in ts ]

ex = InstanceBasedLearningExtractor(tmpls)

urls = (
    'http://www.rc-chem.eu/doprava', # should fail
    'http://www.rc-chem.eu/produkty/2-fma',
    'http://www.rc-chem.eu/produkty/3-fmc',
    'http://www.rc-chem.eu/produkty/3-mmc-crystal',
    'http://www.rc-chem.eu/produkty/4-fa-crystal',
    'http://www.rc-chem.eu/produkty/dimethylone',
    'http://www.rc-chem.eu/produkty/ethylphenidate',
    'http://www.rc-chem.eu/produkty/mpa',
    'http://www.rc-chem.eu/produkty/neb',
    'http://www.rc-chem.eu/produkty/pentedrone-velky-crystal',
    'http://www.rc-chem.eu/produkty/thio-crystal',
    'http://www.rc-chem.eu/produkty/thio-velky-crystal',
    'http://mefedronprodej.webnode.cz/produkty-1/',
)



for u in urls: #('file:///home/pborky/tmp/test/test1.html', 'file:///home/pborky/tmp/test/test2.html', 'file:///home/pborky/tmp/test/test3.html', 'file:///home/pborky/tmp/test/test4.html'):
    page = url_to_page(u)
    extract = {}
    e = ex.extract(page)
    if e[0] is None:
        print 'FAILED to extract from %s.' %u
        continue
    for ee in e[0]:
        extract.update(ee)
    values = {
        'URL_PROD': u,
    }
    for k,v in extract.iteritems():
        values[k] = v[0]

    name = values.get('NAME_PROD')
    chem = values.get('CHEM_NAME_PROD')

    if not name or len(values) < 3:
        print 'FAILED to extract from %s.' %u
        continue

    pg,_ = Page.objects.get_or_create(site=site, name=name)
    pr,_ = Product.objects.get_or_create(page=pg, group=group)
    pi = ProductInfo.objects.create(product=pr)

    pg.url = u
    pr.chem = chem

    for k,v in values.iteritems():
        d = KeyValueDescriptor.objects.get(symbol=k)
        kv = KeyValue.objects.create(descriptor=d, value=v)
        pi.values.add(kv)

    pg.save()
    pr.save()
    pi.save()

    print 'EXTRACTED from %s:' % u
    pprint.pprint(ex.extract(page)[0])


