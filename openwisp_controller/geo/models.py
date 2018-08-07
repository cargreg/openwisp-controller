from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from openwisp_users.mixins import OrgMixin, ValidateOrgMixin
from django.contrib.gis.db import models
from django_loci.base.models import AbstractFloorPlan, AbstractObjectLocation
from django.utils.translation import ugettext_lazy as _
from django_google_maps.fields import AddressField, GeoLocationField
from openwisp_utils.base import TimeStampedEditableModel
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
import uuid


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('openwisp_users.Organization',
                                     verbose_name=_('organization'),
                                     on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(choices=[('outdoor', 'Outdoor environment (eg: street, square, garden, land)'),
                            ('indoor', 'Indoor environment (eg: building, roofs, subway, large vehicles)')],
                            help_text='indoor locations can have floorplans associated to them',
                            max_length=8, blank=True, null=True)
    is_mobile = models.BooleanField(help_text='is this location a moving object?', verbose_name='is mobile?')
    created = AutoCreatedField(_('created'), editable=False)
    modified = AutoLastModifiedField(_('modified'), editable=False)
    address = AddressField(max_length=100, blank=True, null=True)
    geolocation = GeoLocationField(blank=True, null=True)

    def __str__(self):
        return self.name

    def clean(self):
        self._validate_outdoor_floorplans()

    def _validate_outdoor_floorplans(self):
        """
        if a location type is changed from indoor to outdoor
        but the location has still floorplan associated to it,
        a ValidationError will be raised
        """
        if self.type == 'indoor' or self._state.adding:
            return
        if self.floorplan_set.count() > 0:
            msg = 'this location has floorplans associated to it, ' \
                  'please delete them before changing its type'
            raise ValidationError({'type': msg})

    @property
    def short_type(self):
        return _(self.type.capitalize())


class FloorPlan(OrgMixin, AbstractFloorPlan):
    location = models.ForeignKey(Location, models.CASCADE)

    class Meta(AbstractFloorPlan.Meta):
        abstract = False

    def clean(self):
        if self.location:
            self.organization = self.location.organization
        self._validate_org_relation('location')
        super(FloorPlan, self).clean()


class ObjectLocation(TimeStampedEditableModel):
    LOCATION_TYPES = (
        ('outdoor', _('Outdoor')),
        ('indoor', _('Indoor')),
        ('mobile', _('Mobile')),
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=36, db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    location = models.ForeignKey('geo.Location', models.PROTECT,
                                 blank=True, null=True)
    floorplan = models.ForeignKey('geo.Floorplan', models.PROTECT,
                                  blank=True, null=True)
    indoor = models.CharField(_('indoor position'), max_length=64,
                              blank=True, null=True)

    class Meta:
        abstract = True
        unique_together = ('content_type', 'object_id')

    def _clean_indoor_location(self):
        """
        ensures related floorplan is not
        associated to a different location
        """
        # skip validation if the instance does not
        # have a floorplan assigned to it yet
        if not self.location or self.location.type != 'indoor' or not self.floorplan:
            return
        if self.location != self.floorplan.location:
            raise ValidationError(_('Invalid floorplan (belongs to a different location)'))

    def _raise_invalid_indoor(self):
        raise ValidationError({'indoor': _('invalid value')})

    def _clean_indoor_position(self):
        """
        ensures invalid indoor position values
        cannot be inserted into the database
        """
        # stop here if location not defined yet
        # (other validation errors will be triggered)
        if not self.location:
            return
        # do not allow non empty values for outdoor locations
        if self.location.type != 'indoor' and self.indoor not in [None, '']:
            self._raise_invalid_indoor()
        # allow empty values for outdoor locations
        elif self.location.type != 'indoor' and self.indoor in [None, '']:
            return
        # split indoor position
        position = []
        if self.indoor:
            position = self.indoor.split(',')
        # must have at least e elements
        if len(position) != 2:
            self._raise_invalid_indoor()
        # each member must be convertible to float
        else:
            for part in position:
                try:
                    float(part)
                except ValueError:
                    self._raise_invalid_indoor()

    def clean(self):
        self._clean_indoor_location()
        self._clean_indoor_position()


class DeviceLocation(ValidateOrgMixin, AbstractObjectLocation):
    # remove generic foreign key attributes
    # (we use a direct foreign key to Device)
    content_type = None
    object_id = None
    # reuse the same generic attribute name used in django-loci
    content_object = models.OneToOneField('config.Device', models.CASCADE)
    # override parent foreign key targets
    location = models.ForeignKey('geo.location', models.PROTECT,
                                 blank=True, null=True)
    floorplan = models.ForeignKey('geo.floorplan', models.PROTECT,
                                  blank=True, null=True)

    class Meta(AbstractObjectLocation.Meta):
        abstract = False
        # remove AbstractObjectLocation.Meta.unique_together
        unique_together = None

    def clean(self):
        self._validate_org_relation('location', field_error='location')
        self._validate_org_relation('floorplan', field_error='floorplan')
        super(DeviceLocation, self).clean()

    @property
    def device(self):
        return self.content_object

    @property
    def organization_id(self):
        return self.device.organization_id


# maintain compatibility with django_loci
Location.objectlocation_set = Location.devicelocation_set
FloorPlan.objectlocation_set = FloorPlan.devicelocation_set
