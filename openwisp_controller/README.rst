openwisp-controller
===================

Dependencies
------------

*  openwisp
*  django_google_maps
*  sqlparse     

Install
-------

Replace the openwisp_controller module

Modify settings.py
	add the  google api key GOOGLE_MAPS_API_KEY = "xxxxxx"
	add django_google_maps in installed_apps 

.. code-block:: python

    INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    # openwisp2 admin theme
    # (must be loaded here)
    'openwisp_utils.admin_theme',
    # all-auth
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_extensions',
    # openwisp2 modules
    'openwisp_users',
    'openwisp_controller.pki',
    'openwisp_controller.config',
    'openwisp_controller.geo',
    # admin
    'django.contrib.admin',
    'django.forms',
    # other dependencies
    'sortedm2m',
    'reversion',
    'leaflet',
    'rest_framework',
    'rest_framework_gis',
    'channels',
    'django_google_maps',
	]
	
	GOOGLE_MAPS_API_KEY = "xxxxxxxxxxxxxxxx"


Run the migrate command ./admin.py migrate

Run the collect static command ./manage.py collectstatic

Reboot
