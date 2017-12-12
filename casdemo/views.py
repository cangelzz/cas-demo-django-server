from dingding.client import ClientWrapper
from django.contrib.auth import authenticate, login, logout
from django.template.response import TemplateResponse
from django.contrib import messages
from django.conf import settings
from django.shortcuts import *


def index(request):
    if request.user.is_authenticated():
        from security.utils import get_roles, get_permissions
        roles = get_roles(request.user)
        permissions = get_permissions(request.user)
        return TemplateResponse(request, "index.html", {"roles": roles, "permissions": permissions})

    return TemplateResponse(request, "index.html", {})

def login_user(request):
    if request.POST:
        username = request.POST.get("username", "").rsplit("\\")[-1].split("@")[0]
        password = request.POST.get("password", "")
        next = request.POST.get("next", "/")
        if username and password:
            user = authenticate(username=username, password=password, request=request)
        else:
            user = None
        if user is not None:
            login(request, user)
            response = redirect(next)
            return response

        messages.error(request, "账号密码有误，请重试")

    #For dingding auto logging
    next = request.GET.get("next", "/")
    if request.from_device in ["pc", "mobile"]:
        from_device = request.from_device
        client = ClientWrapper("portal")
        data = client.get_request_signature(request.build_absolute_uri())
        data["agent_id"] = client.corpinfo["config"][2]
        data["corp_id"] = client.corpinfo["config"][0]
        data["from"] = from_device
        data["next"] = next
        data["form_title"] = "正在尝试自动登录..."
        return TemplateResponse(request, "login_dingding.html", data)

    action = request.GET.get("action", "")
    data = {
        "next": next,
        "action": action,
        "ding_user_id": request.GET.get("ding_user_id")
    }
    if action == "bind":
        data["form_title"] = "请登录域帐号以绑定钉钉"
    else:
        data["form_title"] = "请登录域帐号"

    return TemplateResponse(request, "login.html", data)


def logout_user(request):
    logout(request)
    request.session.pop("logged_ding_user_id", None)
    request.session.pop("verified", None)
    next = request.GET.get("next", "/")
    return redirect(next)
