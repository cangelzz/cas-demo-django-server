import json
from .models import DingUser, ChatGroup
from .client import ClientWrapper
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.contrib.auth import login, logout
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import logging
from django.core.mail import send_mail
from datetime import datetime
from django.conf import settings
import os
import re
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

log = logging.getLogger(__name__)


def index(request):
    if request.session.get("logged_ding_user_id"):
        return redirect("/")

    from_device = request.from_device  # GET.get("from", None)
    if from_device is None:
        if not request.user.is_authenticated():
            return redirect("/login/?next=/dingding/")

        if not request.user.dinguser.user_id:
            return TemplateResponse(request, "dingding/index_browser.html", {})

        request.session["logged_ding_user_id"] = request.user.dinguser.user_id
        return redirect("/")

    client = ClientWrapper()
    data = client.get_request_signature(request.build_absolute_uri())
    data["agent_id"] = client.corpinfo["config"][2]
    data["corp_id"] = client.corpinfo["config"][0]
    data["from"] = from_device

    return TemplateResponse(request, "dingding/index.html", data)


def login_user(request):
    code = request.GET.get("code")
    next = request.GET.get("next", "/")
    avatar = request.GET.get("avatar", "")
    nick = request.GET.get("nick", "")
    client = ClientWrapper()
    is_success, result = client.get_user_info(code)
    if is_success:
        user_id = result.get("userid")
        if not user_id:
            log.warning("userid is none from result: " + json.dumps(result, indent=2, ensure_ascii=False))
            return redirect("/")
        try:
            try:
                dinguser = DingUser.objects.get(user_id=user_id)
            except DingUser.MultipleObjectsReturned:
                log.warning("DingUser has multiple objects for user_id:" + user_id)
                dinguser = DingUser.objects.filter(user_id=user_id).first()
            if nick:
                dinguser.name = nick
            if avatar:
                dinguser.avatar = avatar
            dinguser.save()

            user = dinguser.aduser
            if request.user.is_authenticated and request.user.username != user.username:
                logout(request)

            login(request, user, "casdemo.auth.ActiveDirectoryAuthenticationBackEnd")
            request.session["logged_ding_user_id"] = user_id

            return redirect(next)
        except DingUser.DoesNotExist:
            return redirect("/login/?next=/dingding/&action=bind&ding_user_id=%s" % user_id)

    return HttpResponse("ERROR get code")
