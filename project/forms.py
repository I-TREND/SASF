__author__ = 'pborky'

from django import forms
from bootstrap_toolkit.widgets import BootstrapTextInput, BootstrapPasswordInput

class LoginForm(forms.Form):

    username = forms.CharField (
        label='',
        max_length=100,
        required=True,
        widget=BootstrapTextInput(attrs={'placeholder': 'Username'}),
    )
    password = forms.CharField (
        label='',
        max_length=100,
        required=True,
        widget=BootstrapPasswordInput(attrs={'placeholder': 'Password'}),
    )