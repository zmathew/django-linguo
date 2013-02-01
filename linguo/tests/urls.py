try:
    from django.conf.urls import patterns, url, include
except ImportError:  # For backwards compatibility with Django < 1.4
    from django.conf.urls.defaults import patterns, url, include

from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)
