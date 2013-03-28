from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic.simple import direct_to_template
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_change
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from rapidsms_httprouter.urls import urlpatterns as router_urls
from ureport.urls import urlpatterns as ureport_urls
from contact.urls import urlpatterns as contact_urls
#from tracking.urls import urlpatterns as tracking_urls
from generic.urls import urlpatterns as generic_urls
from ussd.urls import urlpatterns as ussd_urls
from message_classifier.urls import urlpatterns as class_urls
from rapidsms.backends.kannel.views import KannelBackendView


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    # RapidSMS core URLs
    (r'^accounts/', include('rapidsms.urls.login_logout')),
#     url(r'^$', 'rapidsms.views.dashboard', name='rapidsms-dashboard'),
    # RapidSMS contrib app URLs
#    (r'^export/', include('rapidsms.contrib.export.urls')),
    url(r'^httptester/$',
        'rapidsms.contrib.httptester.views.generate_identity',
        {'backend_name': 'message_tester'}, name='httptester-index'),
    (r'^httptester/', include('rapidsms.contrib.httptester.urls')),
    (r'^locations/', include('rapidsms.contrib.locations.urls')),
    (r'^messagelog/', include('rapidsms.contrib.messagelog.urls')),
    (r'^messaging/', include('rapidsms.contrib.messaging.urls')),
    (r'^registration/', include('rapidsms.contrib.registration.urls')),
#    (r'^scheduler/', include('rapidsms.contrib.scheduler.urls')),
    url(r"^backend/kannel-fake-smsc/$", KannelBackendView.as_view(backend_name="kannel-fake-smsc")),
#    url(r"^router/receive/$", KannelBackendView.as_view(backend_name="smsbu")),
    url(r"^backend/leom/$", KannelBackendView.as_view(backend_name="leom")),
    url(r"^backend/econet/$", KannelBackendView.as_view(backend_name="econet")),
    url(r"^router/receive/$", KannelBackendView.as_view(backend_name="kan2http")),
    url(r'^$', direct_to_template, {'template':'ureport/home.html'}, name="new_home"),
    url(r'^join/$', direct_to_template, {'template':'ureport/how_to_join.html'}),
    url(r'^about_ureport/$', direct_to_template, {'template':'ureport/about.html'}),
    url(r'^ureport-admin/$', 'ureport.views.ureport_content', {'slug':'ureport_home', 'base_template':'ureport/three-square.html', 'num_columns':3}, name='rapidsms-dashboard'),
#    url('^accounts/login', 'rapidsms.views.login'),
#    url('^accounts/logout', 'rapidsms.views.logout'),
    url('^accounts/change_password', login_required(password_change), {'template_name':'ureport/change_password.html', 'post_change_redirect':'/'}),
    (r'^polls/', include('poll.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) +\
    router_urls + ureport_urls + contact_urls + generic_urls + ussd_urls + class_urls 

#In development, static files should be served from app static directories
urlpatterns += staticfiles_urlpatterns()
