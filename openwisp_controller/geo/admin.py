from django.contrib import admin
from django.forms.widgets import TextInput
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Location, FloorPlan, DeviceLocation
from ..admin import MultitenantAdminMixin
from django_loci.base.admin import (AbstractFloorPlanForm, AbstractFloorPlanAdmin,
                                    AbstractFloorPlanInline, AbstractObjectLocationForm,
                                    ObjectLocationMixin)
from openwisp_utils.admin import MultitenantOrgFilter
from ..config.admin import DeviceAdmin as BaseDeviceAdmin
from ..config.admin import ConfigInline
from ..config.models import Device
from django.conf.urls import url
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django_google_maps.widgets import GoogleMapsAddressWidget
from django_google_maps.fields import AddressField, GeoLocationField
from django.contrib.gis.db import models
from django.conf import settings


class FloorPlanForm(AbstractFloorPlanForm):
    class Meta(AbstractFloorPlanForm.Meta):
        model = FloorPlan
        exclude = ('organization',)  # automatically managed


class FloorPlanAdmin(MultitenantAdminMixin, AbstractFloorPlanAdmin):
    form = FloorPlanForm
    list_filter = [('organization', MultitenantOrgFilter),
                   'created']


FloorPlanAdmin.list_display.insert(1, 'organization')


class FloorPlanInline(AbstractFloorPlanInline):
    form = FloorPlanForm
    model = FloorPlan


class _GoogleMapsAddressWidget(GoogleMapsAddressWidget):
    template_name = "google_maps/widgets/map_widget.html"


class LocationModelAdmin(admin.ModelAdmin):

    list_display = ['name', 'short_type', 'is_mobile', 'created', 'modified']
    search_fields = ['name', 'address']
    list_filter = ['type', 'is_mobile']
    inlines = [FloorPlanInline]
    save_on_top = True
    formfield_overrides = {
        AddressField: {
            'widget': _GoogleMapsAddressWidget(attrs={'data-map-type': 'roadmap'})},
        GeoLocationField: {
            'widget': TextInput(attrs={
                'readonly': 'readonly'
            })
        },
    }

    def get_urls(self):
        # hardcoding django_loci as the prefix for the
        # view names makes it much easier to extend
        # without having to change templates
        app_label = 'django_loci'
        return [
            url(r'^(?P<pk>[^/]+)/json/$',
                self.admin_site.admin_view(self.json_view),
                name='{0}_location_json'.format(app_label)),
            url(r'^(?P<pk>[^/]+)/floorplans/json/$',
                self.admin_site.admin_view(self.floorplans_json_view),
                name='{0}_location_floorplans_json'.format(app_label))
        ] + super(LocationModelAdmin, self).get_urls()

    def json_view(self, request, pk):
        instance = get_object_or_404(self.model, pk=pk)
        return JsonResponse({
            'name': instance.name,
            'type': instance.type,
            'is_mobile': instance.is_mobile,
            'address': instance.address,
            'geolocation': str(instance.geolocation),
        })

    def floorplans_json_view(self, request, pk):
        instance = get_object_or_404(self.model, pk=pk)
        choices = []
        for floorplan in instance.floorplan_set.all():
            choices.append({
                'id': floorplan.pk,
                'str': str(floorplan),
                'floor': floorplan.floor,
                'image': floorplan.image.url,
                'image_width': floorplan.image.width,
                'image_height': floorplan.image.height,
            })
        return JsonResponse({'choices': choices})


LocationModelAdmin.list_display.insert(1, 'organization')
LocationModelAdmin.list_filter.insert(0, ('organization', MultitenantOrgFilter))


class ObjectLocationForm(AbstractObjectLocationForm):

    location = models.ForeignKey('geo.Location', models.PROTECT, blank=True, null=True)
    floorplan = models.ForeignKey('geo.Floorplan', models.PROTECT, blank=True, null=True)

    geolocation = forms.CharField(widget=forms.TextInput(attrs={'id': 'id_geolocation',
                                                         'style': 'display: block;', }), required=False)

    address = forms.CharField(widget=forms.TextInput(attrs={'id': 'id_address'}), required=False)

    class Media:
        css = {
            'all': (settings.STATIC_URL +
                    'django_google_maps/css/google-maps-admin.css', )
        }
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/3.1.0/jquery.min.js',
            'https://maps.google.com/maps/api/js?key={}&libraries=places'.format(
                settings.GOOGLE_MAPS_API_KEY),
            'django-loci/js/loci.js',
            settings.STATIC_URL + 'django_google_maps/js/google-maps-admin.js',
        )

    class Meta(AbstractObjectLocationForm.Meta):
        model = DeviceLocation

    def __init__(self, *args, **kwargs):
        super(AbstractObjectLocationForm, self).__init__(*args, **kwargs)
        # set initial values for custom fields
        initial = {}
        obj = self.instance
        location = obj.location
        floorplan = obj.floorplan
        if location:
            initial.update({
                'location_selection': 'existing',
                'type': location.type,
                'is_mobile': location.is_mobile,
                'name': location.name,
                'address': location.address,
                'geolocation': location.geolocation,
            })
        if floorplan:
            initial.update({
                'floorplan_selection': 'existing',
                'floorplan': floorplan.pk,
                'floor': floorplan.floor,
                'image': floorplan.image
            })
            floorplan_choices = self.fields['floorplan'].choices
            self.fields['floorplan'].choices = floorplan_choices + [(floorplan.pk, floorplan)]
        self.initial.update(initial)

    def _get_floorplan_instance(self):
        floorplan = super(ObjectLocationForm, self)._get_floorplan_instance()
        floorplan.organization_id = self.data.get('organization')
        return floorplan

    def clean(self):
        data = self.cleaned_data
        type_ = data['type']
        is_mobile = data['is_mobile']
        msg = _('this field is required for locations of type %(type)s')
        fields = []
        if not is_mobile and type_ in ['outdoor', 'indoor']:
            fields += ['location_selection', 'name', 'address', 'geolocation']
        if not is_mobile and type_ == 'indoor':
            fields += ['floorplan_selection', 'floor', 'indoor']
            if data.get('floorplan_selection') == 'existing':
                fields.append('floorplan')
            elif data.get('floorplan_selection') == 'new':
                fields.append('image')
        elif is_mobile and not data.get('location'):
            data['name'] = ''
            data['address'] = ''
            data['geolocation'] = ''
            data['location_selection'] = 'new'
        for field in fields:
            if field in data and data[field] in [None, '']:
                params = {'type': type_}
                err = ValidationError(msg, params=params)
                self.add_error(field, err)

    def _get_location_instance(self):
        data = self.cleaned_data
        location = data.get('location') or self.location_model()
        location.type = data.get('type') or location.type
        location.is_mobile = data.get('is_mobile') or location.is_mobile
        location.name = data.get('name') or location.name
        location.address = data.get('address') or location.address
        location.geolocation = data.get('geolocation')
        return location

    # def save(self, commit=True):
    #     instance = self.instance
    #     data = self.cleaned_data
    #     # create or update location
    #     #instance.location = self._get_location_instance()
    #     location = self._get_location_instance()
    #     print(data)
    #     print(data['content_object'])
    #     #location.organization_id = data['organization']
    #     # set name of mobile locations automatically
    #     id = uuid.uuid4().hex
    #     location.id = id
    #     location.organization_id = self.data.get('organization')
    #     location.is_mobile=data['is_mobile']
    #     if data['is_mobile'] and not location.name:
    #         location.name = str(self.instance.content_object)
    #     #location.save()
    #     instance.location=location
    #     # create or update floorplan
    #     if data['type'] == 'indoor':
    #         floorplan = self._get_floorplan_instance()
    #         floorplan.save()
    #         instance.floorplan = floorplan
    #     # call super
    #     return super(AbstractObjectLocationForm, self).save(commit=True)
    def save(self, commit=True):
        instance = self.instance
        print(instance)
        data = self.cleaned_data
        print(data)
        print(data['content_object'].organization_id)
        # create or update location
        instance.location = self._get_location_instance()
        # set name of mobile locations automatically
        if data['is_mobile'] and not instance.location.name:
            instance.location.name = str(self.instance.content_object)
        instance.location.organization_id = data['content_object'].organization_id
        instance.location.is_mobile = data['is_mobile']
        instance.location.save()
        # create or update floorplan
        if data['type'] == 'indoor':
            instance.floorplan = self._get_floorplan_instance()
            instance.floorplan.save()
        # call super
        return super(AbstractObjectLocationForm, self).save(commit=True)


class DeviceLocationInline(ObjectLocationMixin, admin.StackedInline):
    model = DeviceLocation
    form = ObjectLocationForm

    fieldsets = (
        (None, {'fields': ('location_selection',)}),
        ('Geographic coordinates', {
            'classes': ('loci', 'coords'),
            'fields': ('location', 'type', 'is_mobile',
                       'name', 'address', 'geolocation'),
        }),
        ('Indoor coordinates', {
            'classes': ('indoor', 'coords'),
            'fields': ('floorplan_selection', 'floorplan',
                       'floor', 'image', 'indoor',),
        })
    )


admin.site.register(FloorPlan, FloorPlanAdmin)
admin.site.register(Location, LocationModelAdmin)


# Add DeviceLocationInline to config.DeviceAdmin

class GeoDeviceAdmin(BaseDeviceAdmin):
    inlines = [DeviceLocationInline, ConfigInline]


admin.site.unregister(Device)
admin.site.register(Device, GeoDeviceAdmin)
