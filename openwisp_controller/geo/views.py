from django.views.generic import FormView
from .forms import LocationForm


class LocationFormView(FormView):
    form_class = LocationForm
    template_name = "geo/index.html"
