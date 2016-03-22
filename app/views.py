import json
import csv
import logging

import re
from scrapely import page_to_dict
from django.contrib import messages
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponse
from django.contrib.auth import get_user
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from quirks.functional import combinator
from quirks.iterable import first

from .forms import SearchForm, SiteContentForm, SiteContentReadOnlyForm, WhoisReadOnlyForm, SiteDataForm, SiteForm, SearchResultForm
from .models import SearchResult, SiteCategory, Search, Site, SIteContent, SiteAttributes, Engine, Ip, Whois, SiteData, SiteAnalyticsDescriptor, SiteAnalytics, Product, ProductInfo, KeyValue, KeyValueDescriptor, ScraperDescriptor, ScraperTemplate, SiteInfo, PrintScreen
from project.helpers import view_GET, view_POST, get_group
from project.addrutil import addrutil, get_ip_hash
from project.searches import engines, full_html_page
from .util import do_search, url_depath, is_categorizing, is_success

logger = logging.getLogger(__name__)

@view_GET(
    r'^$',
    template = 'home.html',
)
def home(request, *args, **kwargs):
    pass

@view_GET(
    r'^search/$',
    template = 'search.html',
    form_cls = {'search':SearchForm,},
    invalid_form_msg = 'You must select engine and enter query string.',
)
def search(request, forms):
    pass

@view_POST(
    r'^search/do$',
    redirect_to='search_results',
    redirect_fallback = 'search',
    form_cls = {'search':SearchForm,},
    invalid_form_msg = 'You must select engine and enter query string.',
)
def search_submit(request, forms):
        form = forms['search']
        if not form.is_valid():
            return {}
        data = form.data
        query = data.get('q')
        engine = data.get('engine')

        if not query:
            return {}

        engine = Engine.objects.get(id=engine)

        if engine.symbol not in engines:
            return {}

        search = do_search(query, engine, user=get_user(request), count=100)

        if not search:
            return {}

        return { 'searchid': search.id }

def get_category(request, group = None):
    if not group:
        group = get_group(request)
    default_category = None
    try:
        default_category = SiteCategory.objects.get(default=True,group__in = (group,))
        default_category = default_category.symbol
    except:
        pass
    return request.GET.get('category', default_category)

def get_csv(results, file):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % file
    writer = csv.writer(response)
    analytics_headers = [
        'DAILY_ADDS_REVENUE',
        'DAILY_PAGEVIEW',
        'GLOBAL_RANK',
        'LINKS_IN',
        'MONTHLY_PAGEVIEWS',
        'MONTHLY_USERS',
        'PAGEVIEWS_PER_VISITOR',
        'TIME_ON_SITE'
    ]
    writer.writerow([
        "DATE_SEARCH_ENGIN","SEARCH_ENGIN_ENGIN","SEARCH_STRING_ENGIN","URL_ENGIN",
        "URL_NUMBER_ENGIN","IP_SHOP", "IP_CODE_SHOP", "DOMAIN_OWNER_CONTACT", "DOMAIN_OWNER_ADDRESS2", "DOMAIN_FROM",
    ] + analytics_headers)

    for result in results:
        content = SIteContent.objects.filter(site=result.site.site)
        content = content.latest('date') if content else None
        attr = SiteAttributes.objects.filter(site=result.site.site)
        attr = attr.latest('date') if attr else None
        ip=country=contact=address2=date_from= 'n/a'
        try:
            if attr:
                if attr.ip.exists():
                    data = [(get_ip_hash(i.address),i.country) for i in attr.ip.all() if i.country and i.address]
                    if data:
                        ip,country = map(','.join, zip(*data))
                if attr.whois.exists():
                    whois= attr.whois.order_by('date_from')
                    contact = hash(whois[0].contact) if whois[0].contact else  'n/a' # current contact hashed
                    address2 = whois[0].address2 if whois[0].address2 else  'n/a' # current contact
                    dt = whois.reverse()[0].date_from
                    date_from = dt.strftime('%Y/%m/%d') if dt else 'n/a'   # first registration
        except Exception as e:
            logger.exception(e)
        descriptors = SiteAnalyticsDescriptor.objects.filter(active=True)
        analytics = []
        for d in  descriptors:
            sa = SiteAnalytics.objects.filter(descriptor=d, site=result.site.site)
            if sa:
                analytics += sa.latest('date').analytics.all()

        analytics = dict(map(lambda a: (a.mapping.symbol.lower(),a.value), analytics))
        map(lambda a: analytics[a].encode('utf8')  if a in analytics else 'None', map(str.lower, analytics_headers) )
        def an_cnv (a):
            m = re.match(r'^([0-9,]+)', a.strip())
            return int(m.group(1).replace(',', '')) if m else a
        def utf_cnv(s):
            return s.encode('utf-8') if isinstance(s,unicode) else s
        row = [
            result.site.found.date.strftime('%Y/%m/%d'),
            result.site.found.engine.symbol,
            result.site.found.q,
            result.site.site.url,
            result.seq,
            ip,
            country,
            contact,
            address2,
            date_from,
            ]
        row += map(
            lambda a: an_cnv(analytics[a])  if a in analytics else 'n/a',
            map(str.lower, analytics_headers)
        )
        writer.writerow(map(utf_cnv, row))
    return response

def paginate(results, page, pagelen = 10, visible = 4):
    paginator = Paginator(results, pagelen)
    try:
        try:
            results = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = 1
            results = paginator.page(page)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            page = paginator.num_pages
            results = paginator.page(page)
        page = int(page)
        if not visible:
            ranges = []
        elif not page - visible > 1:
            visible = 2*visible
            ranges = filter(lambda x:x>0 and x<=paginator.num_pages,range(1,2+visible))
        elif not page + visible < paginator.num_pages:
            visible = 2*visible
            ranges = filter(lambda x:x>0 and x<=paginator.num_pages,range(paginator.num_pages-visible,paginator.num_pages+1))
        else:
            ranges = filter(lambda x:x>0 and x<=paginator.num_pages,range(page - visible, page + visible + 1))

        if page - visible > 1:
            ranges =  [0] + ranges
        if page + visible < paginator.num_pages:
            ranges =  ranges + [0]

        return results, ranges, page
    except Exception as e:
        logger.error(e)
    return results, [], page

@view_GET(
    r'^search/(?P<searchid>\d*)/$',
    template = 'search.html',
    form_cls = {'search':SearchForm },
    invalid_form_msg = 'You must select engine and enter query string.',
)
def search_results(request, searchid, forms ):

    group = get_group(request)
    category = get_category(request, group)
    format = request.GET.get('format')
    page = request.GET.get('page','1')
    q = request.GET.get('find','')

    try:
        search = Search.objects.get(id=int(searchid), group=group)
    except:
        return HttpResponseNotFound()

    if is_categorizing(search):
        messages.warning(request, 'Categorization under progress. Try refresh to check status.')
    else:
        s = is_success(search)
        if s is not None:
            if s:
                messages.success(request, 'Categorization succesfully ended.')
            else:
                messages.error(request, 'Categorization failed.')

    forms['search'] = forms['search2'] = SearchForm(instance=search, request=request)

    categories = SiteCategory.objects.filter(active=True, group__in=(group,)).order_by("id")
    if search:
        results = SearchResult.objects.filter(search = search)

        if q:
            results = results.filter(site__site__url__icontains=q)

        categories = list((cat,results.filter(site__category=cat,site__banned=False).count()) for cat in categories)
        result_counts = dict(
            banned = 0, # speed up # results.filter(site__banned=True).count(),
            other = results.filter(site__category__isnull=True,site__banned=False).count(),
        )

        if category:
            if category == 'banned':
                results = results.filter(site__banned=True)
            else:
                if category == 'other':
                    results = results.filter(site__category__isnull=True, site__banned=False)
                else:
                    results = results.filter(site__category__symbol=category, site__banned=False)

        results = results.order_by('-site__fresh', 'site__site__name','seq')
    else:
        categories = list((cat,0) for cat in categories)
        result_counts = dict(banned=0, other=0)
        results = []

    if format == 'csv':
        return get_csv(results, category)
    else:
        results, pages, _ = paginate(results, page, 15)
        return {
            'forms': forms,
            'results':  results,
            'pages':  pages,
            'categories': categories,
            'category': category,
            'result_counts': result_counts,
            'q': q,
            'search': search,
            }

@view_GET(
    r'^search/all$',
    template = 'search.html',
)
def search_results_all(request, forms):

        group = get_group(request)
        category = get_category(request, group)
        format = request.GET.get('format')
        page = request.GET.get('page','1')
        q = request.GET.get('find','')

        categories = SiteCategory.objects.filter(active=True, group__in=(group,)).order_by("id")
        results = SearchResult.objects.filter(search__group = group).distinct('site__id','site__fresh', 'site__site__name')

        if q:
            results = results.filter(site__site__url__icontains=q)

        categories = list((cat,results.filter(site__category=cat,site__banned=False).count()) for cat in categories)
        result_counts = dict(
            banned = 0, # speed up # results.filter(site__banned=True).count(),
            other = results.filter(site__category__isnull=True,site__banned=False).count(),
        )

        if category:
            if category == 'banned':
                results = results.filter(site__banned=True)
            else:
                if category == 'other':
                    results = results.filter(site__category__isnull=True, site__banned=False)
                else:
                    results = results.filter(site__category__symbol=category, site__banned=False)

        results = results.order_by('-site__fresh', 'site__site__name')

        if format == 'csv':
            return get_csv(results, category)
        else:
            results, pages, _ = paginate(results, page, 15)

            return {
                'forms': forms,
                'results': results,
                'pages': pages,
                'categories': categories,
                'category': category,
                'result_counts': result_counts,
                'q': q,
                }

@view_GET(
    r'^search/new$',
    template = 'search.html',
    form_cls = {'add': SearchForm},
)
def search_new(request, forms):
    return

@view_POST(
    r'^search/add$',
    redirect_to='search_results',
    redirect_attr='nexturl',
    form_cls = {'add': SearchForm},
)
def search_add(request, forms):
    group = get_group(request)
    form = forms['add']
    if not form.is_valid():
        return HttpResponseServerError()
    form.save()
    search = form.instance
    search.manual = True
    search.group = group
    search.save()
    messages.success(request, 'Data successfuly saved.')

    return {
        'searchid': search.id
    }

@view_GET(
    r'^search/(?P<searchid>\d*)/site/new$',
    template = 'site-new-ajax.html',
)
def site_new(request, forms, searchid):
    category = get_category(request)
    search = Search.objects.get(id=int(searchid))
    nexturl = request.GET.get('nexturl')
    forms = {
        'site': SiteForm(),
        #'site_data': SiteDataForm(),
        'search_result': SearchResultForm(),
        }
    return {
        'forms' : forms,
        'nexturl': nexturl,
        'searchid': search.id,
        'category': category,
    }

def category_changed(site):
    try:

        category = site.category.symbol if site.category else '-'
        descriptor = KeyValueDescriptor.objects.get(symbol='CATEGORY_SHOP', target__symbol = 'SiteInfo' )

        sis = SiteInfo.objects.filter(site=site, values__descriptor__in = (descriptor,))
        if sis.exists():
            si = sis.latest()
            category_old =  si.dict.get('CATEGORY_SHOP')
            if category_old == category:
                return

        si = SiteInfo.objects.create(site=site, automatic=False)
        si.values.add(KeyValue.objects.create(descriptor=descriptor, value=category))
        si.save()

    except:
        logger.exception('Can\'t save history.')

@view_POST(
    r'^search/(?P<searchid>\d*)/site/add$',
    form_cls = {
        'site': SiteForm,
        'search_result': SearchResultForm,
        },
)
def site_add(request, forms, searchid):
    group = get_group(request)
    search = Search.objects.get(id=int(searchid))
    nexturl = request.GET.get('nexturl')
    site_form = forms['site']
    search_result_form = forms['search_result']

    try:
        # TODO move it to Model constructor
        site = Site.objects.get(url=url_depath(site_form.data.get('url')))
        site_form = SiteForm(request.POST, instance=site)
    except:
        pass

    sequence = search_result_form.data.get('sequence')
    if not site_form.is_valid() or not search_result_form.is_valid():
        return

    site=site_form.save()

    try:
        site_data = SiteData.objects.get(site=site, group=group)
    except:
        site_data = SiteData.objects.create(site=site, group=group,found=search)

    category = get_category(request, group)
    if category:
        if category == 'banned':
            site_data.banned = True
        else:
            site_data.banned = False
            if category == 'other':
                site_data.category = None
            else:
                site_data.category = SiteCategory.objects.get(symbol = category)

    category_changed(site_data)

    site_data.manual = True
    site_data.save()

    search_result = SearchResult.objects.filter(site=site_data, search=search)
    if search_result:
        search_result = search_result[0]
    else:
        search_result = SearchResult(site=site_data, search=search, )

    str2list = combinator(
        lambda s: list(s) if isinstance(s,tuple) else [s],
        lambda s: eval(s) if s else tuple()
    )
    list2str = lambda s: ','.join(map(str,s))

    sequence = str2list(sequence)
    if search_result:
        sequence += str2list(search_result.sequence)
    sequence = sorted(set(sequence))

    search_result.sequence = list2str(sequence)
    search_result.seq = sequence[0] if len(sequence)>0 else 0
    search_result.save()

def update_site_details(site, attributes):

    try:
        res = addrutil(site.url) # add data from DNS & WHOIS

        ips = set(map(
            lambda ip: Ip.objects.get_or_create(**ip)[0],
            res.get('addresses',())
        ))
        whois = set(map(
            lambda whois: Whois.objects.get_or_create(**whois)[0],
            res.get('whois',())
        ))

        if ips != frozenset(attributes.ip.all()) or whois != frozenset(attributes.whois.all()):
            site_attr = SiteAttributes(site=site)
            site_attr.save()

            if whois:
                site_attr.whois.add(*whois)
            elif attributes:
                site_attr.whois.add(*attributes.whois.all())

            if ips:
                site_attr.ip.add(*ips)
            elif attributes:
                site_attr.ip.add(*attributes.ip.all())

            site_attr.save()

            attributes =  site_attr

    except:
        pass

    return attributes

def get_site_details(siteid, update= False):
    site = SiteData.objects.get(id=int(siteid))

    content = attributes = ip = whois = None

    try:
        content = SIteContent.objects.filter(site=site.site ).latest('date')
    except:
        pass

    try:
        attributes = SiteAttributes.objects.filter(site=site.site ).latest('date')
    except:
        pass

    if update:
        attributes = update_site_details(site.site, attributes)

    if attributes:
        ip = first(attributes.ip.all())
        whois = first(attributes.whois.all())
    return site,content,whois,ip


@view_GET(
    r'^site-content/(?P<siteid>\d*)/detail$',
    template = 'site-content-ajax.html',
)
def site_content_detail(request, forms, siteid):
        nexturl = request.GET.get('nexturl')
        try:
            site,content,whois,ip = get_site_details(siteid)
        except:
            return HttpResponseNotFound()

        return {
            'site': site,
            'nexturl': nexturl,
            'detail': {
                'content':   SiteContentReadOnlyForm(instance=content) if content else SiteContentReadOnlyForm() ,
                'whois':   WhoisReadOnlyForm(instance=whois) if whois else WhoisReadOnlyForm(),
                #'ip':   IpReadOnlyForm(instance=ip) if ip else IpReadOnlyForm(),
                }
        }
@view_GET(
    r'^site-content/(?P<siteid>\d*)/edit$',
    template = 'site-content-ajax.html',
)
def site_content_edit(request, forms, siteid):
        nexturl = request.GET.get('nexturl')
        try:
            site,content,whois,ip = get_site_details(siteid)
        except:
            return HttpResponseNotFound()

        return {
            'site': site,
            'nexturl': nexturl,
            'detail': {
                'content':  SiteContentReadOnlyForm(instance=content) if content else SiteContentReadOnlyForm() ,
                'whois':   WhoisReadOnlyForm(instance=whois) if whois else WhoisReadOnlyForm(),
                #'ip':   IpReadOnlyForm(instance=ip) if ip else IpReadOnlyForm(),
                'edit': SiteDataForm(request=request,instance=site),
                }
        }

@view_POST(
    r'^site-content/edit$',
    form_cls = {'edit': SiteContentForm},
)
def site_edit(request, forms):
        form = forms['edit']
        if not form.is_valid():
            return HttpResponseServerError()
        form.save()
        messages.success(request, 'Data successfuly saved.')
        return HttpResponse()

@view_POST(
    r'^site/edit$',
    redirect_to='search',
    redirect_attr='nexturl',
    #form_cls = {'edit': SiteForm,},
)
def site_edit_name(request, forms):
        site = SiteData.objects.get(id=int(request.POST['siteid']))
        form = SiteDataForm(request.POST, instance=site)
        if not form.is_valid():
            return HttpResponseServerError()
        form.save()
        site.fresh = False
        site.save()
        messages.success(request, 'Data successfuly saved.')

@view_POST(
    r'^site/category/edit$',
    redirect_to='search',
    redirect_attr='nexturl',
    form_cls = None,
)
def site_edit_category(request, forms):
        site = SiteData.objects.get(id=int(request.POST['siteid']))
        site.category = SiteCategory.objects.get(id=int(request.POST['category'])) if request.POST['category'] else None
        site.save()
        category_changed(site)
        messages.success(request, 'Data successfuly saved.')


@view_POST(
    r'^sites/category/edit$',
    redirect_to='search',
    redirect_attr='nexturl',
    form_cls = None,
)
def sites_edit_category(request, forms):
    category = request.POST['selected-sites-category']
    site_data_ids = map(int,( v for k,v in request.POST.iteritems() if re.match(r'site-[0-9]*',k) ))
    if category == 'banned':
        for site_data in SiteData.objects.filter(id__in= site_data_ids):
            if site_data.fresh:
                site_data.fresh = False
            site_data.banned = True
            site_data.save()
    else:
        category = SiteCategory.objects.get(symbol=category) if category != 'other' else None
        for site_data in SiteData.objects.filter(id__in= site_data_ids):
            if site_data.banned:
                site_data.banned = False
            if site_data.fresh:
                site_data.fresh = False
            site_data.category = category
            site_data.save()
            category_changed(site_data)
    messages.success(request, 'Data successfuly saved.')

@view_POST(
    r'^site/banned/edit$',
    redirect_to='search',
    redirect_attr='nexturl',
    form_cls = None,
)
def site_ban(request, forms):
        site, = SiteData.objects.filter(id=int(request.POST['siteid']))
        site.banned = not site.banned
        site.fresh = False
        site.save()
        if site.banned:
            messages.success(request, 'Site "%s" added to ban-list.' % (site.site.name,))
        else:
            messages.success(request, 'Site "%s" removed from ban-list.' % (site.site.name,))

@view_POST(
    r'^product/banned/edit$',
    redirect_to='scrap',
    redirect_attr='nexturl',
    form_cls = None,
)
def product_ban(request, forms):
    product, = Product.objects.filter(id=int(request.POST['productid']))
    product.banned = not product.banned
    product.save()
    if product.banned:
        messages.success(request, 'Product "%s" added to ban-list.' % (product.page.name,))
    else:
        messages.success(request, 'Product "%s" removed from ban-list.' % (product.page.name,))


@view_GET(
    r'^scrap$',
    template = 'scrap.html',
)
def scrap(request, *args, **kwargs):
    page = request.GET.get('page','1')
    banned = 'banned' in request.GET
    group = get_group(request)
    results = Product.objects.filter(group=group,banned=banned)
    results, pages, _ = paginate(results, page, 15)
    return {
        'results': results,
        'pages': pages,
        'banned': banned,
    }

@view_GET(
    r'^scrap/site/(?P<siteid>\d*)/$',
    template = 'scrap.html',
)
def scrap_site(request, siteid,  *args, **kwargs):
    page = request.GET.get('page','1')
    banned = 'banned' in request.GET
    group = get_group(request)
    sd = SiteData.objects.filter(id=siteid, group=group)
    if sd.exists():
        sd = sd[0]
        results = Product.objects.filter(page__site=sd,banned=banned)
    else:
        results = []
        sd = None
    scrapers = ScraperDescriptor.objects.filter(site=sd)
    results, pages, _ = paginate(results, page, 15)
    descriptors = KeyValueDescriptor.objects.filter(active=True, group__in=(group,), )
    return {
        'site': sd,
        'results': results,
        'pages': pages,
        'scrapers': scrapers,
        'descriptors': descriptors,
        'screenshots': PrintScreen.objects.filter(site=sd).order_by('-date'),
        'banned': banned,
        }

@view_GET(
    r'^scrap/site/(?P<siteid>\d*)/(?:(?P<scraperid>\d*)/)?edit$',
    template = 'product-info-ajax.html',
)
def scrap_site_edit(request, siteid, scraperid= None,  *args, **kwargs):
    group = get_group(request)
    site= SiteData.objects.get(id=siteid)
    descriptors =  KeyValueDescriptor.objects.filter(active=True, visible=True, group__in=(group,), target__symbol='ProductInfo').order_by('order')
    items = {}
    scraper = None
    if scraperid:
        scraper = ScraperDescriptor.objects.filter(id=scraperid)
        if scraper.exists():
            scraper = scraper[0]
        items = dict((i.descriptor.symbol, i)  for i in scraper.items.all())
    results = [(items.get(d.symbol),d) for d in descriptors if d.symbol != 'URL_PROD']
    return {
        'site': site,
        'scraper': scraper,
        'results': results,
        'edit': True,
        }

@view_GET(
    r'scrap/plugin',
    template = 'scrap-plugin.html',
    content_type = 'application/json',
)
def scrap_plugin(request, *args, **kwargs):
    group = get_group(request)
    descriptors =  KeyValueDescriptor.objects.filter(active=True, group__in=(group,), target__symbol='ProductInfo').order_by('order')
    return {
       'descriptors': descriptors,
    }

def get_info(queryset, descriptors, edit = False):
    results_fixed = {}
    results = {}
    for pi in queryset.order_by('-date'):
        if pi.automatic:
            results.update((v.descriptor.symbol,v) for v in pi.values.all() if v.descriptor.symbol not in results)
        else:
            results_fixed.update((v.descriptor.symbol,v) for v in pi.values.all() if v.descriptor.symbol not in results)
    results.update(results_fixed)
    return [(results.get(d.symbol),d) for d in descriptors if edit or d.symbol in results]

def get_info_csv(queryset, descriptors, filename):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
    writer = csv.writer(response)
    writer.writerow(['DATE', 'AUTOMATIC'] + [d.symbol for d in descriptors])
    def utf_cnv(s):
        return s.encode('utf-8') if isinstance(s,unicode) else s
    for i in queryset.order_by('-date'):
        values = i.dict
        # '{:%Y-%m-%d %H:%M:%S.%f}'.format(i.date)
        writer.writerow([ i.date, i.automatic ]+map(utf_cnv, (values.get(d.symbol,'') for d in descriptors)))
    return response

@view_GET(
    r'scrap/(?P<typ>product|site|history)(?:/(?P<attr>\w+))?/export$',
)
def scrap_export(request, typ, attr, *args, **kwargs):
    group = get_group(request)

    site = request.GET.get('site', None)
    product = request.GET.get('product', None)

    category = ('approved',)
    qs = []
    descriptors =  KeyValueDescriptor.objects.filter(active=True, group__in=(group,),)

    if typ == 'product':
        qs = ProductInfo.objects.filter(product__page__site__category__symbol__in = category)
        if site:
            qs = qs.filter(product__page__site__id=site)
        descriptors =  descriptors.filter(target__symbol='ProductInfo')
        fn = 'product_info'
    elif typ == 'site':
        qs = SiteInfo.objects.filter(site__category__symbol__in = category)
        if site:
            qs = qs.filter(site__id = site)
        descriptors =  descriptors.filter(target__symbol='SiteInfo')
        fn = 'site_info'
    elif typ == 'history':
        descriptors =  descriptors.filter(symbol = attr)
        if not descriptors.exists():
            return
        if all(map(lambda d: d.target.symbol == 'SiteInfo', descriptors)):
            qs = SiteInfo.objects.filter(site__category__symbol__in = category, values__descriptor__in = descriptors)
            if site:
                qs = qs.filter(site__id = site)
        elif all(map(lambda d: d.target.symbol == 'ProductInfo', descriptors)):
            qs = ProductInfo.objects.filter(product__page__site__category__symbol__in = category, values__descriptor__in = descriptors)
            if product:
                qs = qs.filter(product__id=product)
        fn = '%s_history' % descriptors[0].symbol
    else:
        return

    descriptors =  descriptors.order_by('order')
    return get_info_csv(qs, descriptors, fn)


@view_GET(
    r'^scrap/product/(?P<productid>\d*)/(?P<edit>edit)?$',
    template = 'product-info-ajax.html',
)
def scrap_product_info(request, productid, edit,  *args, **kwargs):
    edit = edit == 'edit'
    group = get_group(request)
    descriptors =  KeyValueDescriptor.objects.filter(active=True, group__in=(group,), target__symbol='ProductInfo').order_by('order')
    product = Product.objects.get(id=productid)
    results = get_info(ProductInfo.objects.filter(product__id=productid), descriptors, edit=edit)
    return {
        'product': product,
        'results': results,
        'edit': edit,
        }

@view_GET(
    r'^scrap/site-info/(?P<siteid>\d*)/(?P<edit>edit)?$',
    template = 'product-info-ajax.html',
)
def scrap_site_info(request, siteid, edit, *args, **kwargs):
    edit = edit == 'edit'
    group = get_group(request)
    descriptors =  KeyValueDescriptor.objects.filter(active=True, group__in=(group,), target__symbol='SiteInfo').order_by('order')
    site = SiteData.objects.get(id=siteid)
    results = get_info(SiteInfo.objects.filter(site__id=siteid), descriptors, edit=edit)
    return {
        'sitedata': site,
        'results': results,
        'edit': edit,
        }

@view_POST(
    r'^scrap/product/edit$',
    template = 'product-info-ajax.html',
)
def scrap_info_edit_do(request,  *args, **kwargs):
    #page = request.GET.get('page','1')
    group = get_group(request)
    siteid = request.POST.get('siteid')
    productid = request.POST.get('productid')
    scraperid = request.POST.get('scraperid')
    sitedataid = request.POST.get('sitedataid')
    descriptors = KeyValueDescriptor.objects.filter(active=True, group__in=(group,))
    product = Product.objects.filter(id=productid, group__in=(group,))
    site = SiteData.objects.filter(id=siteid, group__in=(group,))
    sitedata = SiteData.objects.filter(id=sitedataid, group__in=(group,))
    scraper = ScraperDescriptor.objects.filter(id=scraperid)
    if sitedata.exists():
        descriptors = descriptors.filter(target__symbol='SiteInfo')
    else:
        descriptors = descriptors.filter(target__symbol='ProductInfo')

    kvs = []
    for d in descriptors:
        if d.symbol in request.POST:
            if site and d.symbol == 'URL_PROD':
                continue
            if sitedata.exists() and d.symbol == 'URL_SHOP':
                continue
            val = request.POST.get(d.symbol).strip()
            if val:
                kvs.append(KeyValue.objects.create(descriptor=d,value=val))

    if kvs:
        if sitedata.exists():
            si = SiteInfo.objects.create(site=sitedata[0], automatic=False)
            si.values.add(*kvs)
            si.save()
        elif product.exists():
            pi = ProductInfo.objects.create(product=product[0], automatic=False)
            pi.values.add(*kvs)
            pi.save()
        else:
            url = request.POST['URL_PROD']
            name = request.POST['NAME_PROD']
            if not scraper.exists():
                if site.exists():
                    scraper = ScraperDescriptor.objects.create(site=site[0] )
                else:
                    return
            else:
                scraper = scraper[0]
            scraper.url=url
            scraper.name=name
            scraper.items.clear()
            scraper.items.add(*kvs)
            scraper.save()

            page = full_html_page(url)
            obj = json.dumps(page_to_dict(page))
            for st in ScraperTemplate.objects.filter(descriptor=scraper):
                st.active = False
            st = ScraperTemplate.objects.create(descriptor=scraper, value=obj)
            st.save()
