from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^/?$', views.storlet_list),
    url(r'^/(?P<storlet_id>[0-9]+)/?$', views.storlet_detail),
    url(r'^/(?P<storlet_id>[0-9]+)/data/?$', views.StorletData.as_view()),
    url(r'^/(?P<account>\w+)/deploy/?$', views.storlet_list_deployed),

    #Deploy to tenant container or object
    url(r'^/(?P<account>\w+)/deploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_deploy),
    url(r'^/(?P<account>\w+)/(?P<container>\w+)/deploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_deploy),
    url(r'^/(?P<account>\w+)/(?P<container>\w+)/(?P<swift_object>\w+)/deploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_deploy),

    #Undeploy to tenant container or object
    url(r'^/(?P<account>\w+)/undeploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_undeploy),
    url(r'^/(?P<account>\w+)/(?P<container>\w+)/undeploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_undeploy),
    url(r'^/(?P<account>\w+)/(?P<container>\w+)/(?P<swift_object>\w+)/undeploy/(?P<storlet_id>[0-9]+)/?$', views.storlet_undeploy),

    url(r'^/dependencies/?$', views.dependency_list),
    url(r'^/dependencies/(?P<dependency_id>\w+)/?$', views.dependency_detail),
    url(r'^/dependencies/(?P<dependency_id>\w+)/data/?$', views.DependencyData.as_view()),
    url(r'^/dependencies/(?P<account>\w+)/deploy/?$', views.dependency_list_deployed),
    url(r'^/dependencies/(?P<account>\w+)/deploy/(?P<dependency_id>\w+)/?$', views.dependency_deploy),
    url(r'^/dependencies/(?P<account>\w+)/undeploy/(?P<dependency_id>\w+)/?$', views.dependency_undeploy)
]
