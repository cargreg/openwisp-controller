from django import forms
from .models import Location
from django_google_maps.widgets import GoogleMapsAddressWidget


class LocationForm(forms.ModelForm):

    class Meta(object):
        model = Location
        fields = '__all__'
        widgets = {
            "address": GoogleMapsAddressWidget,
        }
