from django.http.response import *
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.views.generic import ListView
from dingding.client import ClientWrapper
import re
from .utils import *
from django.db.models import F
from django.conf import settings
from django.db.models import Q
from .models import *


@csrf_exempt
def api_auth_user(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    if not username or not password:
        return JsonResponse({"ret": False, "errmsg": "Empty username or password"})

    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({"ret": False, "errmsg": "Bad username or password"})

    return JsonResponse({"ret": True, "errmsg": "user authenticated"})


def auth_application(func):
    @csrf_exempt
    def _auth(request, *args, **kwargs):
        app_id = request.META.get("HTTP_APPID", request.GET.get("appId"))
        if not app_id:
            return HttpResponseBadRequest("No APPID in the header or querystring")

        app_secret = request.META.get("HTTP_APPSECRET", request.GET.get("appSecret"))
        if not app_secret:
            return HttpResponseBadRequest("No APPSECRET in the header or querystring")
        try:
            app = Application.objects.get(id=app_id, secret=app_secret)
            if not app.active:
                return HttpResponseForbidden("Application is disabled")
        except Application.DoesNotExist:
            return HttpResponseBadRequest("Wrong APPID or APPSECRET")
        except:
            return HttpResponseBadRequest("Bad APPID or APPSECRET")

        return func(request, app, *args, **kwargs)

    return _auth


@auth_application
def api_query_user(request, app, username):
    user = get_object_or_404(User, username=username)
    return JsonResponse(
        {
            "roles.list": get_roles(user, app.name, "list"),
            "permissions.list": get_permissions(user, app.name, "list"),
            "urls.list": get_urls(user, app.name, "list"),
            "properties": get_properties(user, app.name, "dict")
        }
    )


@auth_application
def api_validate_user_permissions(request, app=None):
    username = request.GET.get("username", request.GET.get("userId", ""))
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"ret": False, "errmsg": "No such user: " + username})

    permissions = request.GET.get("permissions")
    if not permissions:
        return JsonResponse({"ret": False, "errmsg": "No permissions in the querystring"})

    type = request.GET.get("type", "all")
    if not type in ["all", "any"]:
        return JsonResponse({"ret": False, "errmsg": "Type %s is not available" % type})

    permissions = set(filter(None, permissions.split("|")))
    user_permissions = set(get_permissions(user, app, "list"))

    if type == "all":
        invalid = permissions.difference(user_permissions)
        if len(invalid) > 0:
            return JsonResponse({"ret": False, "errmsg": "Not have: %s permission[s]" % "|".join(invalid)})
        else:
            return JsonResponse({"ret": True, "errmsg": "User has all the permissions"})

    if type == "any":
        intersect = permissions.intersection(user_permissions)
        if len(intersect) > 0:
            return JsonResponse({"ret": True, "errmsg": "User has %s permission[s]" % "|".join(intersect)})
        else:
            return JsonResponse({"ret": False, "errmsg": "User does not have any permissions"})

    return HttpResponseBadRequest("You should not see this")


@auth_application
def api_validate_user_roles(request, app=None):
    username = request.GET.get("username", request.GET.get("userId", ""))
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"ret": False, "errmsg": "No such user: " + username})

    roles = request.GET.get("roles")
    if not roles:
        return JsonResponse({"ret": False, "errmsg": "No roles in the querystring"})

    type = request.GET.get("type", "all")
    if not type in ["all", "any"]:
        return JsonResponse({"ret": False, "errmsg": "Type %s is not available" % type})

    roles = set(filter(None, roles.split("|")))
    user_roles = get_roles(user, app, "list")

    if type == "all":
        invalid = set(roles).difference(user_roles)
        if len(invalid) > 0:
            return JsonResponse({"ret": False, "errmsg": "Not have: %s role[s]" % ("|").join(invalid)})
        else:
            return JsonResponse({"ret": True, "errmsg": "User has all the roles"})

    if type == "any":
        intersect = set(roles).intersection(user_roles)
        if len(intersect) > 0:
            return JsonResponse({"ret": True, "errmsg": "User has %s role[s]" % "|".join(intersect)})
        else:
            return JsonResponse({"ret": False, "errmsg": "User does not have any roles"})

    return HttpResponseBadRequest("You should not see this")


@auth_application
def api_urls(request, app=None):
    username = request.GET.get("username")
    if not username:
        return JsonResponse({"status": "error", "msg": "no username"})

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "msg": "user %s does not exist" % username})

    user_urls = get_urls(user, app.name, "list")

    return JsonResponse({"status": "ok", "urls.list": user_urls})


@auth_application
def api_permissions_add(request, app=None):
    name = request.POST.get("name")
    if not name:
        return HttpResponseBadRequest("Permission name is missing")

    description = request.POST.get("description")
    permission, new = Permission.objects.get_or_create(application=app, name=name,
                                                       defaults={"description": description})
    if not new:
        permission.description = description
        permission.save(update_fields=["description"])

    return JsonResponse(
        {"status": new and "created" or "updated", "name": name, "description": description, "app": app.name})


@csrf_exempt
def add_acl(request):
    if not request.method == "POST":
        return HttpResponseBadRequest("不支持的方法")

    type = request.POST.get("type")
    if not type in ["role", "permission"]:
        return HttpResponseBadRequest("类型错误")

    acl = get_object_or_404(ACL, user__username=request.POST.get("username"))
    object_id = request.POST.get("id")
    if type == "role":
        role = get_object_or_404(Role, id=object_id)
        if request.user.is_superuser or role.application.can_manage(request.user):
            acl.roles.add(role)
            return TemplateResponse(request, "security/includes/role.html", {"role": role})

    if type == "permission":
        permission = get_object_or_404(Permission, id=object_id)
        if request.user.is_superuser or permission.application.can_manage(request.user):
            acl.permissions.add(permission)
            return TemplateResponse(request, "security/includes/permission.html", {"permission": permission})

    return HttpResponseForbidden("没有权限进行此操作")


@csrf_exempt
def remove_acl(request):
    if not request.method == "POST":
        return HttpResponseBadRequest("不支持的方法")

    type = request.POST.get("type")
    if not type in ["role", "permission"]:
        return HttpResponseBadRequest("类型错误")

    acl = get_object_or_404(ACL, user__username=request.POST.get("username"))
    object_id = request.POST.get("id")
    if type == "role":
        role = get_object_or_404(Role, id=object_id)
        if request.user.is_superuser or role.application.can_manage(request.user):
            acl.roles.remove(role)
            return HttpResponse("OK")

    if type == "permission":
        permission = get_object_or_404(Permission, id=object_id)
        if request.user.is_superuser or permission.application.can_manage(request.user):
            acl.permissions.remove(permission)
            return HttpResponse("OK")

    return HttpResponseBadRequest("操作未成功")


@auth_application
def api_user(request, app):
    username = request.GET.get("username")
    if not username:
        return JsonResponse({"status": "error", "msg": "no username"})

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "msg": "user %s does not exist" % username})

    result = {
        "username": username,
        "fullname": user.profile.fullname(),
        "name": user.profile.full_name,
        "mobile": user.dinguser.mobile or user.profile.mobile,
        "ding_user_id": user.dinguser.user_id,
        "avatar": user.dinguser.avatar_url,
        "roles": get_roles(user, app.name, "list"),
        "permissions": get_permissions(user, app.name, "list"),
        "urls": get_urls(user, app.name, "list"),
        "properties": get_properties(user, app.name, "dict"),
        "department": user.profile.ou.name
    }
    return JsonResponse(result)


@auth_application
def api_users(request, app):
    result = {}
    role_name = request.GET.get("role")
    if role_name:
        try:
            result["role"] = role_name
            role = Role.objects.get(application=app, name=role_name)
            result["users"] = list(role.assigned_acls.values_list("user__username", flat=True))

        except Role.DoesNotExist:
            result["users"] = []

    permission_name = request.GET.get("permission")
    if permission_name:
        try:
            result["permission"] = permission_name
            permission = Permission.objects.get(application=app, name=permission_name)
            acls = permission.assigned_acls.all()
            for role in permission.roles.all():
                acls = acls | role.assigned_acls.all()

            acls = acls.distinct()
            result["users"] = list(
                acls.annotate(username=F("user__username"), name=F("user__profile__full_name"), department=F("user__profile__ou__name")).values("username",
                                                                                                                                                "name",
                                                                                                                                                "department"))

        except Permission.DoesNotExist:
            result["users"] = []

    return JsonResponse(result)
