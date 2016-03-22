from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import Group, User
from django.db.models import Model, CharField, BooleanField, FloatField, URLField, ForeignKey, ManyToManyField,\
                            DateField, GenericIPAddressField, DateTimeField, IntegerField, CommaSeparatedIntegerField,\
                            TextField, ImageField


class CompressedTextField(TextField):
    '''transparently compress data before hitting the db and uncompress after fetching'''
    def to_python(self, value):
        if not value:
            return value

        try:
            return value.decode('base64').decode('bz2').decode('utf-8')
        except Exception:
            return value

    def get_prep_value(self, value):
        if not value:
            return value

        try:
            value.decode('base64')
            return value
        except Exception:
            try:
                tmp = value.encode('utf-8').encode('bz2').encode('base64')
            except Exception:
                return value
            else:
                if len(tmp) > len(value):
                    return value

                return tmp

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^app\.models\.CompressedTextField"])

def flag(obj, attr, true, false, none):
    return (true if getattr(obj,attr) else false) if hasattr(obj, attr) else none

def active_flag(obj, true = '', false = '-', none = ''):
    return flag(obj,'active', true, false, none)

def banned_flag(obj, true = '-', false = '', none = ''):
    return flag(obj,'banned', true, false, none)

class Engine(Model):
    name = CharField(max_length=100, verbose_name='Name of Search Engine', unique=True)
    symbol = CharField(max_length=10, verbose_name='Search Engine Code', unique=True)
    group = ManyToManyField(Group, blank=True)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s' %(active_flag(self),  self.name,)
    class Meta:
        ordering = ["-active", "name"]
        verbose_name = "Search Engine"
        permissions = (("can_edit_engines", "Can edit search engines"),)

class SiteCategory(Model):
    name = CharField(max_length=100, verbose_name='Site Category', unique=True)
    symbol = CharField(max_length=10, verbose_name='Category Code', unique=True)
    default = BooleanField(verbose_name='Default', default=False)
    group = ManyToManyField(Group, blank=True)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s' %(active_flag(self),  self.name,)
    class Meta:
        ordering = ["-active", "name"]
        verbose_name = "Site Category"
        verbose_name_plural = "Site Categories"

class SiteType(Model):
    name =  CharField(max_length=100, verbose_name='Shop Type', unique=True)
    symbol = CharField(max_length=10, verbose_name='Type Code', unique=True)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s' %(active_flag(self),  self.name,)
    class Meta:
        ordering = ["-active", "name"]
        verbose_name = "Shop Type"

class ShipmentMethod(Model):
    name = CharField(max_length=100, verbose_name='Shipment Method', unique=True)
    symbol = CharField(max_length=10, verbose_name='Shipment Method Code', unique=True)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s' %(active_flag(self),  self.name,)
    class Meta:
        ordering = ["-active", "name"]
        verbose_name = "Shipment Method"

class Keyword(Model):
    keyword =  CharField(verbose_name='Keyword',max_length=200, unique=True)
    group = ManyToManyField(Group, blank=True)
    category = ForeignKey(SiteCategory)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s (%s; Groups: %s)' % (active_flag(self), self.keyword,unicode(self.category),', '.join(map(unicode,self.group.all())))
    class Meta:
        ordering = ["-active", "keyword"]
        verbose_name = "Keyword"

class Site(Model):
    name = CharField(max_length=200, verbose_name='Name of Site')
    url = URLField(verbose_name='URL of Site', unique=True)
    def __unicode__(self):
        return u'%s (%s)' %(self.name, self.url)
    class Meta:
        ordering = ["name"]
        verbose_name = "Site"

class SiteData(Model):
    site = ForeignKey(Site)
    group = ForeignKey(Group)
    fresh = BooleanField(default=False, verbose_name='Fresh')
    category = ForeignKey(SiteCategory, verbose_name='Category of Site', null=True, blank=True)
    banned = BooleanField(verbose_name='Banned')
    manual = BooleanField(verbose_name='Manually added', default=False)
    categorized = BooleanField(verbose_name='Categorized', default=False)
    found = ForeignKey('Search', related_name='site_found')
    @property
    def name(self):
        return self.site.name
    @property
    def url(self):
        return self.site.url
    def __unicode__(self):
        return u'%s -> %s' %(self.group, self.site)
    class Meta:
        ordering = ["group", "site"]
        verbose_name = "Site Data"
        verbose_name_plural = "Site Data"
        unique_together = [ "site", "group" ]

class PrintScreen(Model):
    date = DateTimeField(verbose_name='Date of PrintScreen',auto_now=True)
    site = ForeignKey(SiteData)
    image = ImageField(upload_to='prntscrn', verbose_name='Image of printscreen')
    class Meta:
        get_latest_by = "date"

class Whois(Model):
    contact = CharField(max_length=200, verbose_name='Contact', null=True, blank=True)
    address1 = CharField(max_length=200, verbose_name='City Address', null=True, blank=True)
    address2 = CharField(max_length=200, verbose_name='Country Address', null=True, blank=True)
    date_from = DateField(verbose_name='Registration Date', null=True, blank=True)
    def __unicode__(self):
        return u'%s' % self.contact
    class Meta:
        ordering = ["contact"]
        verbose_name = "Whois"
        verbose_name_plural = "Whois"
        get_latest_by = "date_from"

class Ip(Model):
    address = GenericIPAddressField(verbose_name='IP Address',unique=True)
    #address_value = IntegerField(verbose_name='IP Address Value')
    country = CharField(max_length=10, verbose_name='Country Code', null=True, blank=True)
    def __unicode__(self):
        return u'%s (%s)' %(unicode(self.address), self.country)
    class Meta:
        ordering = ["country", "address"]
        verbose_name = "IP Address"
        verbose_name_plural = "IP Addresses"

class SiteAttributes(Model):
    date = DateTimeField(verbose_name='Date of Check',auto_now=True)
    site = ForeignKey(Site)
    ip = ManyToManyField(Ip, null=True, blank=True)
    whois = ManyToManyField(Whois, null=True, blank=True)
    def __unicode__(self):
        return u'%s (%s)' %(self.site, self.date)
    class Meta:
        ordering = ["site", "date"]
        verbose_name = "Site Attributes Check"
        get_latest_by = "date"

class SIteContent(Model):
    date = DateTimeField(verbose_name='Date of Check',auto_now=True)
    site = ForeignKey(Site)
    last_update = DateTimeField(verbose_name='Last Update Date', default=None, null=True, blank=True)
    shipment = ManyToManyField(ShipmentMethod)
    type = ForeignKey(SiteType, null=True, blank=True)
    links = ManyToManyField(Site, null=True, blank=True, related_name='link_sites')
    def __unicode__(self):
        return u'%s (%s)' %(self.site, self.date)
    class Meta:
        ordering = ["site", "date"]
        verbose_name = "Site Content Check"
        get_latest_by = "date"

class KeyValueMapping(Model):
    name = CharField(max_length=100, verbose_name='Name')
    symbol = CharField(max_length=100, verbose_name='Symbol')
    value = CharField(max_length=100, verbose_name='XPath')
    active = BooleanField(verbose_name='Active', default=True)
    def __unicode__(self):
        return u'%s %s -> %s' %(active_flag(self), self.name, self.value,)
    class Meta:
        ordering = ["-active", "name", "symbol"]
        verbose_name = "Key-Value Map"

class SiteAnalyticsValue(Model):
    mapping = ForeignKey(KeyValueMapping)
    value = TextField(verbose_name='Value')
    @property
    def name(self):
        return self.mapping.name
    def __unicode__(self):
        return u'%s -> %s' %(self.name, self.value,)
    class Meta:
        ordering = ["mapping",]
        verbose_name = "Analytics Value"

class SiteAnalyticsDescriptor(Model):
    name = CharField(max_length=100, verbose_name='Name of Statistic Provider', unique=True)
    symbol = CharField(max_length=10, verbose_name='Statistic Provider Code', unique=True)
    group = ManyToManyField(Group, blank=True)
    active = BooleanField(verbose_name='Active', default=True)
    url = URLField(verbose_name='URL of Statistic Provider')
    fields = ManyToManyField(KeyValueMapping, null=True, blank=True)
    def __unicode__(self):
        return u'%s %s (%s)' %(active_flag(self),  self.name, ', '.join(k.name for k in self.fields.all()))
    class Meta:
        ordering = ["-active","name",]
        verbose_name = "Site Analytics Descriptor"

class SiteAnalytics(Model):
    date = DateTimeField(verbose_name='Date of Check',auto_now=True)
    site = ForeignKey(Site)
    descriptor = ForeignKey(SiteAnalyticsDescriptor)
    analytics = ManyToManyField(SiteAnalyticsValue, null=True, blank=True)
    def __unicode__(self):
        return u'%s %s' %(self.site, self.descriptor,)
    class Meta:
        ordering = ["site", "date"]
        verbose_name = "Site Analytic"
        get_latest_by = "date"

class Query(Model):
    q = CharField(max_length=200, verbose_name='Search String')
    group = ForeignKey(Group, null=True, blank=True)
    active = BooleanField(verbose_name='Active', default=False)
    def __unicode__(self):
        return u'%s %s (Group: %s)' % (active_flag(self), self.q, self.group)
    class Meta:
        ordering = ["-active", 'group', "q"]
        verbose_name = "Search Query"
        verbose_name_plural = "Search Queries"

class Search(Model):
    date = DateTimeField(verbose_name='Date of Search',auto_now=True)
    engine = ForeignKey(Engine)
    q = CharField(max_length=100, verbose_name='Search String')
    query = ForeignKey(Query, null=True, blank=True)
    group = ForeignKey(Group, null=True, blank=True)
    user = ForeignKey(User, null=True, blank=True)
    manual = BooleanField(verbose_name='Manually added', default=False)
    def __unicode__(self):
        return u'"%s" with %s (%s)' %(self.q, self.engine, self.date)
    class Meta:
        ordering = ["date"]
        verbose_name = "Search"
        verbose_name_plural = "Searches"
        get_latest_by = "date"


class SearchResult(Model):
    search = ForeignKey(Search)
    sequence = CommaSeparatedIntegerField(verbose_name='Sequence Number(s)',max_length=200)
    seq = IntegerField(verbose_name='Best Sequence Number')
    keyword = ManyToManyField(Keyword, null=True, blank=True)
    site = ForeignKey(SiteData)
    def __unicode__(self):
        return u'%s (%s)' %(self.site, self.search.date)
    class Meta:
        ordering = ["site", "search"]
        verbose_name = "Search Result"
        unique_together = [ "search", "site" ]

class Page(Model):
    site = ForeignKey(SiteData)
    url = URLField(verbose_name='Page URL')
    name = CharField(max_length=1000, verbose_name='Page Title', unique=True)
    def __unicode__(self):
        return u'%s (%s)' % ( self.name, self.site, )
    class Meta:
        ordering = ["site__site__name", "name"]
        verbose_name = "Page"

class Product(Model):
    page = ForeignKey(Page)
    group = ForeignKey(Group)
    chem = CharField(max_length=1000, verbose_name='Product Chemical Name', null=True, blank=True)
    banned = BooleanField(verbose_name='Banned')
    @property
    def name(self):
        return self.page.name if self.page else None
    def __unicode__(self):
        return u'%s (%s)' % ( self.name, self.chem, )
    class Meta:
        ordering = ["page"]
        verbose_name = "Product"

class DescriptorTarget(Model):
    name = CharField(max_length=100, verbose_name='Name', unique=True)
    symbol = CharField(max_length=100, verbose_name='Symbol', unique=True)
    active = BooleanField(verbose_name='Active', default=True)
    def __unicode__(self):
        return u'%s %s (%s)' %(active_flag(self), self.symbol,self.name, )
    class Meta:
        ordering = [ '-active', 'symbol' ]
        verbose_name = "Descriptor Target"

class DescriptorType(Model):
    name = CharField(max_length=100, verbose_name='Name', unique=True)
    symbol = CharField(max_length=100, verbose_name='Symbol', unique=True)
    active = BooleanField(verbose_name='Active', default=True)
    def __unicode__(self):
        return u'%s %s (%s)' %(active_flag(self), self.symbol,self.name, )
    class Meta:
        ordering = [ '-active', 'symbol' ]
        verbose_name = "Descriptor Type"


class KeyValueDescriptor(Model):
    name = CharField(max_length=100, verbose_name='Name', unique=True)
    symbol = CharField(max_length=100, verbose_name='Symbol', unique=True)
    desc = CharField(max_length=100, verbose_name='Description')
    value = CharField(max_length=100, verbose_name='Value', null=True, blank=True)
    active = BooleanField(verbose_name='Active', default=True)
    visible = BooleanField(verbose_name='Visible', default=True)
    group = ManyToManyField(Group, blank=True)
    target = ForeignKey(DescriptorTarget)
    typ = ForeignKey(DescriptorType)
    order = IntegerField(verbose_name='Order',default=True)
    def __unicode__(self):
        return u'%s %s.%s (%s; %s)' %(active_flag(self), self.target.symbol, self.symbol, self.name, self.desc, ) #', '.join(map(unicode,self.group.all())),)
    class Meta:
        ordering = [ '-active', 'target', 'order' ]
        verbose_name = "Key Value Descriptor"

class KeyValue(Model):
    descriptor = ForeignKey(KeyValueDescriptor)
    value = CharField(max_length=1000, verbose_name='Value')
    @property
    def name(self):
        return self.descriptor.name
    @property
    def symbol(self):
        return self.descriptor.symbol
    def __unicode__(self):
        return u'%s -> %s' % (self.name, self.value)
    class Meta:
        ordering = [ 'descriptor' ]
        verbose_name = "Key Value"

class ScraperDescriptor(Model):
    name = CharField(max_length=100, verbose_name='Name', null=True, blank=True)
    site = ForeignKey(SiteData)
    url = URLField(verbose_name='Template URL')
    items = ManyToManyField(KeyValue)
    def __unicode__(self):
        return u'%s (%s)' % (self.site, self.name)
    class Meta:
        ordering = [ 'site', 'url' ]
        verbose_name = "Scraper Descriptor"

class ScraperTemplate(Model):
    descriptor = ForeignKey(ScraperDescriptor)
    value = CompressedTextField()
    original = ForeignKey('ScraperTemplate', null=True, blank=True)
    annotated = BooleanField(verbose_name='Annotated', default=False)
    active = BooleanField(verbose_name='Active', default=True)
    @property
    def name(self):
        return self.descriptor.name
    def __unicode__(self):
        return u'%s %s -> %s %s' % ( active_flag(self), self.name, '<blob>', '' if self.annotated else '*')
    class Meta:
        ordering = [ 'descriptor' ]
        verbose_name = "Scraper Template"

class ProductInfo(Model):
    product = ForeignKey(Product)
    automatic = BooleanField(default=True)
    date = DateTimeField(verbose_name='Date of Check',auto_now=True)
    values = ManyToManyField(KeyValue)
    @property
    def dict(self):
        return dict((i.symbol,i.value) for i in self.values.all())
    def __unicode__(self):
        return u'%s (%s)' % (self.product.name, self.date)
    class Meta:
        get_latest_by = "date"
        ordering = [ 'date', 'product' ]
        verbose_name = "Product Information"
        verbose_name_plural = "Product Information"

class SiteInfo(Model):
    site = ForeignKey(SiteData)
    automatic = BooleanField(default=True)
    date = DateTimeField(verbose_name='Date of Check',auto_now=True)
    values = ManyToManyField(KeyValue)
    @property
    def dict(self):
        return dict((i.symbol,i.value) for i in self.values.all())
    def __unicode__(self):
        return u'%s (%s)' % (self.site.name, self.date)
    class Meta:
        get_latest_by = "date"
        ordering = [ 'date', 'site' ]
        verbose_name = "Site Information"
        verbose_name_plural = "Site Information"



