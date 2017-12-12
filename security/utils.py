from .models import *
import json


def _json(queryset, key):
    result = {}
    for q in queryset:
        result.setdefault(q.application.name, [])
        result[q.application.name].append(q.name)

    result_list = []
    for k, v in result.items():
        result_list.append({"application": k, key: result[k]})
    return result_list


def _return(queryset, key, type):
    if type == "queryset":
        return queryset

    if type == "text":
        if key == "urls":
            from urllib.parse import urljoin
            result = "|".join([urljoin(a, p) for a, p in queryset.values_list("application__url", "url")])
        else:
            result = "|".join(["%s:%s" % t for t in queryset.values_list("application__name", "name")])
        return result and result or ""

    if type == "dict":
        return _json(queryset, key)

    if type == "list":
        if key == "urls":
            return list(queryset.values_list("url", flat=True))
        else:
            return list(queryset.values_list("name", flat=True))


def get_roles(user, application_name=None, type="queryset"):
    if application_name:
        if isinstance(application_name, Application):
            queryset = user.acl.roles.filter(application=application_name)
        else:
            queryset = user.acl.roles.filter(application__name=application_name)
    else:
        queryset = user.acl.roles.all()
    return _return(queryset.distinct(), "roles", type)


def get_permissions(user, application_name=None, type="queryset"):
    if application_name:
        if isinstance(application_name, Application):
            params = {"application": application_name}
        else:
            params = {"application__name": application_name}

        queryset = user.acl.permissions.filter(**params)
        for role in user.acl.roles.filter(**params):
            queryset = queryset | role.permissions.filter(**params)
    else:
        queryset = user.acl.permissions.all()
        for role in user.acl.roles.all():
            queryset = queryset | role.permissions.all()

    return _return(queryset.distinct(), "permissions", type)


def get_urls(user, application_name=None, type="queryset"):
    if application_name:
        roles = user.acl.roles.filter(application__name=application_name)
    else:
        return []

    queryset = AppUrl.objects.none()
    for role in roles:
        queryset = queryset | role.urls.all()

    return _return(queryset.distinct(), "urls", type)


def get_properties(user, application_name=None, type="queryset"):
    def _loads(data):
        try:
            return json.loads(data)
        except:
            return {}

    if application_name:
        if isinstance(application_name, Application):
            params = {"application": application_name}
        else:
            params = {"application__name": application_name}

        queryset = Property.objects.filter(acl=user.acl, **params)
    else:
        queryset = Property.objects.filter(acl=user.acl)

    if type == "queryset":
        return queryset
    elif type == "list":
        return list(map(lambda x: {"application": x[0], "properties": _loads(x[1])}, queryset.values_list("application__name", "content")))
    elif type == "dict":
        return queryset.first() and queryset.first().content or {}


def get_user_applications(user):
    return (user.owned_applications.all() | user.managed_applications.all()).distinct()