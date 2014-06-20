from django.conf.urls import patterns, url

from profiles import views


urlpatterns = patterns('',
                       url(r'^(?P<username>[^/]+)/?$',
                           views.profile_detail,
                           name='profiles_profile_detail'),
                       )
