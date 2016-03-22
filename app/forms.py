from django.contrib.auth import get_user
from django.forms import HiddenInput, SelectMultiple, Form, CharField, URLField, BooleanField
from bootstrap_toolkit.widgets import BootstrapDateInput, BootstrapTextInput
from django.utils.html import format_html
from project.helpers import get_group
from project.widgets import ModelForm,Uneditable
from .models import Search, SIteContent, Whois, Ip, Site, SiteData, SearchResult

class SearchForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        if self._request:
            group = get_group(self._request)
            qs = self.fields['engine'].queryset
            self.fields['engine'].queryset = qs.filter(group__in=(group,)).distinct()
    class Meta:
        model = Search
        fields = ('engine', 'q',)
        attrs = {
            'engine': {
                'label': '',
                'empty_label': 'Select engine',
                'queryset': model.engine.get_query_set().filter(active=True),
                },
            'q': {
                'label': '',
                'widget': BootstrapTextInput(attrs={'placeholder': 'Query string'}),
                },
            }

class SearchResultForm(ModelForm):
    class Meta:
        model = SearchResult
        fields = ('id', 'sequence')
        attrs = {
            'id':  {
                'widget': HiddenInput(),
                },
            'sequence': {
                'label': '',
                'widget': BootstrapTextInput(attrs={'placeholder': 'Sequence number(s)'}),
            }
        }


class SiteDataForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SiteDataForm
            , self).__init__(*args, **kwargs)
        if self._request:
            group = get_group(self._request)
            qs = self.fields['category'].queryset
            self.fields['category'].queryset = qs.filter(group__in=(group,)).distinct()
    class Meta:
        model = SiteData
        fields = ('id', 'category', 'fresh', 'banned')
        attrs = {
            'id':  {
                'widget': HiddenInput(),
                },
            'fresh' : {
                'help_text': '',
                },
            'banned' : {
                'help_text': '',
                },
            'name' : {
                'help_text': '',
                'widget': BootstrapTextInput(attrs={'class': 'span11' }),
                },
            'category': {
                'label': '',
                'empty_label': 'Select category',
                'queryset': model.category.get_query_set().filter(active=True),
                },
            }

class SiteForm(ModelForm):
    class Meta:
        model = Site
        fields = ('id', 'name', 'url')
        attrs = {
            'id':  {
                'widget': HiddenInput(),
                },
            'fresh' : {
                'help_text': '',
                },
            'banned' : {
                'help_text': '',
                },
            'name' : {
                'label': '',
                'help_text': '',
                'widget': BootstrapTextInput(attrs={'placeholder': 'Name of the site'}),
                },
            'url' : {
                'label': '',
                'help_text': '',
                'widget': BootstrapTextInput(attrs={'placeholder': 'URL Address'}),
                },
            }

class SiteContentForm(ModelForm):
    class Meta:
        model = SIteContent
        fields = ('site', 'last_update', 'shipment', 'type', 'links')
        attrs = {
            'site': {
                'widget': HiddenInput(),
            },
            'last_update': {
                'label': 'Last updated',
                'widget': BootstrapDateInput(attrs={'class': 'datepicker', 'data-provide':'datepicker-inline' }),
            },
            'shipment': {
                'label': 'Shipment method',
                'help_text': '',
            },
            'type': {
                'label': 'Shop type',
                'empty_label': 'Select shop type'
            },
            'links': {
                'label': 'Links to other sites',
                'help_text': '',
                },
            }


class SiteContentReadOnlyForm(ModelForm):
    class Meta:
        model = SIteContent
        fields = ('site', 'last_update', 'shipment', 'type', 'links')
        attrs = {
            'site': {
                'widget': HiddenInput(attrs={'disabled':True}),
                },
            'last_update': {
                'label': 'Last updated',
                'widget': BootstrapDateInput(attrs={'disabled':True}),
                },
            'shipment': {
                'label': 'Shipment method',
                'help_text': '',
                'widget': Uneditable(
                        value_calback=lambda qs,selected: ', '.join( shp.name for shp in qs if shp.id in selected )
                    ),
                },
            'type': {
                'label': 'Shop type',
                'widget': Uneditable(
                        value_calback=lambda qs,selected: ', '.join( type.name for type in qs if type.id in selected )
                    ),
            },
            'links': {
                'label': 'Links to other sites',
                'help_text': '',
                'widget': Uneditable(
                        value_calback=lambda qs,selected: [format_html(u'<a href="{0}">{1}</a>', lnk.url, lnk.name) for lnk in qs if lnk.id in selected ] ,
                    ),
                },
            }


class WhoisReadOnlyForm(ModelForm):
    class Meta:
        model = Whois
        fields = ('date_from', 'contact', 'address1', 'address2')
        attrs = {
            'date_from': {
                'label': 'Whois registration date',
                'widget': BootstrapDateInput(attrs={'disabled':True}),
                },
            'contact': {
                'label': 'Whois contact',
                'widget': Uneditable(value_calback=lambda qs,selected: ', '.join(filter(None, selected))),
                },
            'address1': {
                'label': 'Whois address (city)',
                'widget': Uneditable(value_calback=lambda qs,selected: ', '.join(filter(None, selected))),
                },
            'address2': {
                'label': 'Whois address (country code)',
                'widget': Uneditable(value_calback=lambda qs,selected: ', '.join(filter(None, selected))),
                },
            }

class IpReadOnlyForm(ModelForm):
    class Meta:
        model = Ip
        fields = ('address', 'country' )
        attrs = {
            'address': {
                'label': 'IP address',
                'widget': Uneditable(),
                },
            'country': {
                'label': 'IP country code',
                'widget': Uneditable( ),
                },
            }