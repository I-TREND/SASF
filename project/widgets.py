
__author__ = 'pborky'

from bootstrap_toolkit.widgets import add_to_css_class
from django.forms import TextInput, ModelForm
from django.forms.models import ModelFormMetaclass
from django.utils.safestring import mark_safe

class FormfieldCallback(object):
    def __init__(self, meta=None, **kwargs):
        if meta is None:
            self.attrs = {}
        elif isinstance(meta, dict):
            self.attrs = meta
        elif hasattr(meta, 'attrs'):
            self.attrs = meta.attrs
        else:
            raise TypeError('Argument "meta" must be dict or must contain attibute "attrs".')
        self.attrs.update(kwargs)

    def __call__(self, field, **kwargs):
        if field.name in self.attrs:
            kwargs.update(self.attrs[field.name])
        queryset_transform = kwargs.pop('queryset_transform', None)
        if callable(queryset_transform):
            pass #field.choices = queryset_transform(field.choices)
        return field.formfield(**kwargs)



class RichModelFormMetaclass(ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        Meta = attrs.get('Meta', None)
        attributes = getattr(Meta, 'attrs', {}) if Meta else {}

        if not attrs.has_key('formfield_callback'):
            attrs['formfield_callback'] = FormfieldCallback(**attributes)
        new_class = super(RichModelFormMetaclass, mcs).__new__(mcs, name, bases, attrs)
        return new_class

class ModelForm(ModelForm):
    __metaclass__ =  RichModelFormMetaclass
    def __init__ (self, *args, **kwargs):
        self._request = kwargs.pop('request', None)
        super(ModelForm,self).__init__ (*args, **kwargs)
        pass

class Uneditable(TextInput):
    def __init__(self, value_calback=None, choices=(), *args,  **kwargs):
        super(Uneditable, self).__init__(*args, **kwargs)
        self.value_calback = value_calback
        self.choices = list(choices)
        self.attrs['disabled'] = True

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        attrs['type'] = 'hidden'
        klass = add_to_css_class(self.attrs.pop('class', ''), 'uneditable-input')
        klass = add_to_css_class(klass, attrs.pop('class', ''))

        base = super(Uneditable, self).render(name, value, attrs)
        if not isinstance(value, list):
            value = [value]
        if self.value_calback:
            if not hasattr(self, 'choices') or isinstance(self.choices, list):
                value = self.value_calback(None, value)
            else:
                value = self.value_calback(self.choices.queryset, value)
        if isinstance(value,list):
            if not value:
                value =  u'<span class="%s" style="color: #555555; background-color: #eeeeee;" disabled="true"></span>' % klass
            else:
                value =  u''.join(u'<span class="%s" style="color: #555555; background-color: #eeeeee;" disabled="true">%s</span>' % (klass, val) for val in value)
        else:
            value = u'<span class="%s" style="color: #555555; background-color: #eeeeee;" disabled="true">%s</span>' % (klass, value)
        return mark_safe(base + value)
