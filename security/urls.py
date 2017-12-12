from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from . import views
from django.conf import settings

urlpatterns = [
    url(r'^acl/add/$', login_required(views.add_acl), name="add_acl"),
    url(r'^acl/remove/$', login_required(views.remove_acl), name="remove_acl")
]

urlpatterns += [
    url(r'^api/validate_user_permissions/$', views.api_validate_user_permissions),
    url(r'^api/validate_user_roles/$', views.api_validate_user_roles),
    url(r'^api/auth/$', views.api_auth_user),
    url(r'^api/query_user/(?P<username>[\w.-]+)/$', views.api_query_user),
    url(r'^api/urls/$', views.api_urls),
    url(r'^api/permissions/add/$', views.api_permissions_add),
    url(r'^api/user/$', views.api_user),
    url(r'^api/users/', views.api_users)
]
