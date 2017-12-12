import requests
from time import time
import uuid
import json
import logging
from hashlib import sha1
from datetime import datetime
from django.contrib.auth.models import User
from .models import ChatGroup, Application

logger = logging.getLogger(__name__)

API_ADDR = "oapi.dingtalk.com"


class ClientNotValidException(Exception):
    pass


def http_get(url, params=None):
    try:
        result = requests.get(url, params)
        try:
            return True, result.json()
        except:
            return False, result.content
    except Exception as e:
        return False, e.message


def http_post(url, data):
    headers = {
        "Content-Type": "application/json",
        "Accept-Charset": "utf-8"
    }
    try:
        result = requests.post(url, json.dumps(data), headers=headers)
        try:
            return True, result.json()
        except:
            return False, result.content
    except Exception as e:
        import traceback
        logger.error(traceback.format_exc())
        return False, e


def token_required(func):
    def wrapper(self, *arg, **kwargs):
        if self.access_token is None:
            self.get_access_token()
        if int(time()) > self.token_expires:
            self.get_access_token()
        return func(self, *arg, **kwargs)

    return wrapper


class Client:
    def __init__(self, CORP_INFO):
        self.corpinfo = CORP_INFO
        self.access_token = None
        self.token_expires = 0
        self.corpid, self.corpsecret, self.agentid = self.corpinfo["config"]

    def auth(self):
        is_success, token = self.get_access_token()
        return is_success

    def get_access_token(self):
        url = "https://%s/gettoken" % (API_ADDR)
        params = {"corpid": self.corpid, "corpsecret": self.corpsecret}
        is_success, result = http_get(url, params)
        if is_success:
            self.access_token = result.get("access_token", None)
            if self.access_token is None:
                raise ClientNotValidException()

            self.token_expires = int(time()) + 3600
            return True, self.access_token

        return False, result

    @token_required
    def get_jsapi_ticket(self):
        url = "https://%s/get_jsapi_ticket" % API_ADDR
        params = {"access_token": self.access_token, "type": "jsapi"}
        return http_get(url, params)

    def get_timestamp(self):
        return str(int(time()))

    def get_noncestr(self):
        return uuid.uuid4().hex

    def sign(self, jsapi_ticket, noncestr, timestamp, url):
        s = "jsapi_ticket=%s&noncestr=%s&timestamp=%s&url=%s" % (jsapi_ticket, noncestr, timestamp, url)
        return sha1(s.encode("utf-8")).hexdigest()

    @token_required
    def get_request_signature(self, url):
        is_success, result = self.get_jsapi_ticket()
        if not is_success:
            return None
        ticket = result["ticket"]
        noncestr = self.get_noncestr()
        timestamp = self.get_timestamp()
        return {"signature": self.sign(ticket, noncestr, timestamp, url), "noncestr": noncestr,
                "timestamp": timestamp, "url": url, "ticket": ticket}

    @token_required
    def get_user(self, user_id):
        url = "https://%s/user/get" % API_ADDR
        params = {
            "access_token": self.access_token,
            "userid": user_id
        }
        return http_get(url, params)

    @token_required
    def get_user_info(self, code):
        url = "https://%s/user/getuserinfo" % API_ADDR
        params = {
            "access_token": self.access_token,
            "code": code
        }
        return http_get(url, params)

    @token_required
    def get_user_simple_list(self, department_id=1):
        url = "https://%s/user/simplelist?" % API_ADDR
        params = {
            "access_token": self.access_token,
            "department_id": department_id,
        }
        return http_get(url, params)

    @token_required
    def get_user_detail_list(self, department_id=1):
        url = "https://%s/user/list?" % API_ADDR
        params = {
            "access_token": self.access_token,
            "department_id": department_id,
        }
        return http_get(url, params)

    @token_required
    def get_department_list(self):
        url = "https://%s/department/list?access_token=%s" % (API_ADDR, self.access_token)
        return http_get(url)

    @token_required
    def get_user_all_list(self, usernames=[]):
        dept_success, result = self.get_department_list()
        if not dept_success:
            return dept_success, result
        users = []
        for department in result["department"]:
            print("getting department %s(%d) ..." % (department["name"], department["id"]))
            us_success, us = self.get_user_detail_list(department["id"])
            if usernames:
                for u in us["userlist"]:
                    adname = u.get("extattr", {}).get("\u57df\u8d26\u53f7", "").split("\\")[-1]
                    if adname in usernames:
                        users.append(u)
            else:
                users.extend(us["userlist"])

        return True, users


class ClientWrapper(Client):
    def __init__(self, app_name="portal"):
        app = Application.objects.get(name=app_name)
        super(ClientWrapper, self).__init__({"config": (app.company.corp_id, app.company.corp_secret, app.agent_id)})


if __name__ == "__main__":
    pass
