from django.conf import settings
from django.apps import AppConfig


class GeoConfig(AppConfig):
    # name = 'openwisp_controller.geo'
    # label = 'geo'
    verbose_name = 'Geographic Information'

    def __setmodels__(self):
        from .models import Location
        self.location_model = Location

    def ready(self):
        super(GeoConfig, self).ready()
        if getattr(settings, 'TESTING', False):
            self._add_params_to_test_config()
