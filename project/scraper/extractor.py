# coding=utf-8
# Scrapely extractors

from __future__ import with_statement
import json

from scrapely import HtmlPage, TemplateMaker, best_match, page_to_dict
from scrapely.extraction import InstanceBasedLearningExtractor
from scrapely.descriptor import FieldDescriptor,ItemDescriptor
from scrapely.extractors import text
from scrapely.template import FragmentAlreadyAnnotated

from app.models import ScraperDescriptor, ScraperTemplate

def load_templates(scraper_id, annotated=True):
    for tmpl in ScraperTemplate.objects.filter(descriptor__id=scraper_id, annotated=annotated, active=True):
        yield tmpl,HtmlPage(**json.loads(tmpl.value))

def pure_text(*args, **kwargs):
    def fnc(txt):
        txt = text(txt)
        return txt.strip()
    return fnc

def price(value, *args, **kwargs):
    import re
    _PRICE = re.compile(u'([A-Z]{3}|[$€\u20ac]|[A-Z]\\w+)?\\s*([\\d\\s-]+(?:[.,]\\d+)?)\\s*([A-Z]{3}|[$€\u20ac]|[A-Z]\\w+)?', re.U)
    #_PRICE = re.compile(r'(€)?(.*)(€)?')
    prc = _PRICE.findall(value)
    if prc:
        currency = prc and prc[0][0] or prc[0][2]
        prefix = bool(prc and prc[0][0])
        _pt = r'(?P<currency>%s)', r'(?P<price>[\d\s-]+(?:[.,]\d+)?)'
        _pt = r'\s*'.join(_pt if prefix else reversed(_pt))
        _pt = re.compile(_pt%currency, re.U)
        def fnc(txt):
            r = _pt.findall(txt)
            return r[0] if r else None
        return fnc
    return lambda txt:None

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
    _PRICE = re.compile(r'([A-Z]{3}|$€|[MGTEmunpd]?[a-zA-Z]+)?\s*([\d\s-]+(?:[.,]\d+)?)\s*([A-Z]{3}|$€|[MGTEmunpd]?[a-zA-Z]+)?', re.U)
    prc = _PRICE.findall(value)
    if prc:
        currency = prc and prc[0][0] or prc[0][2]
        prefix = bool(prc and prc[0][0])
        _pt = r'(?P<measure>%s)', r'(?P<qty>[\d\s-]+(?:[.,]\d+)?)'
        _pt = r'\s*'.join(_pt if prefix else reversed(_pt))
        _pt = re.compile(_pt%currency, re.U)
        def fnc(txt):
            r = _pt.findall(txt)
            return r[0] if r else None
        return fnc
    return lambda txt:None

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


types = {
    'TEXT': pure_text,
    'PRICE': pure_price,
    'CURRENCY': pure_currency,
    'QTY': pure_qty,
    'UNIT': pure_unit,
    }

def get_extractor(site_id):
    sds = ScraperDescriptor.objects.filter(site__id=site_id)
    if not sds.exists():
        return

    tmpls = []

    for s in sds:
        items = s.items.filter(descriptor__target__symbol='ProductInfo')
        idesc = ItemDescriptor('', '', [ FieldDescriptor(i.descriptor.symbol, i.descriptor.desc, extractor=types[i.descriptor.typ.symbol](i.value))  for i in items ] )
        ts = load_templates(s.id)
        tmpls += [ (t, idesc) for _,t in ts ]
    if tmpls:
        ex = InstanceBasedLearningExtractor(tmpls)
        def extractor(response):
            page = HtmlPage(response.url, headers=response.headers, body=response.body.decode(response.encoding), encoding=response.encoding)
            extract = ex.extract(page)
            if extract[0] is not None:
                for e in extract[0]:
                    yield e
        return extractor

def annotate(scraper_id):  #TODO: fix tnis..
    sd = ScraperDescriptor.objects.get(id=scraper_id)
    ts = load_templates(sd.id, False)
    for st,t in ts:
        tms = [TemplateMaker(t)]
        for item in sd.items.all():

            func = best_match(item.value)
            sel = tms[-1].select(func)
            print 'ATTRIBUTE: %s (%s)' % (item.descriptor.symbol,item.value)
            if not sel:
                print 'SKIPPED.'
                continue
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
                    if tm.annotate_fragment(row, item.descriptor.symbol):
                        annotated = True
                        break
                except FragmentAlreadyAnnotated:
                    pass
            if not annotated:
                tms.append(TemplateMaker(t))
                tms[-1].annotate_fragment(row, item.descriptor.symbol)
        ScraperTemplate.objects.filter(original=st).delete()
        for tm in tms:
            obj = json.dumps(page_to_dict(tm.get_template()))
            ScraperTemplate.objects.create(descriptor=sd,annotated=True,original=st,value=obj).save()
