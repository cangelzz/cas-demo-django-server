import re

"""
win
Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrom
e/49.0.2623.110 Safari/537.36 dingtalk-win/1.0.0 nw(0.14.7) DingTalk(3.1.3-RC.0)

android
Mozilla/5.0 (Linux; Android 4.4.4; L55u Build/23.0.1.F.0.98) AppleWebKit/537.36
(KHTML, like Gecko) Version/4.0 Chrome/33.0.0.0 Mobile Safari/537.36 AliApp(Ding
Talk/3.1.0) com.alibaba.android.rimet/0 Channel/10002068 language/zh-CN

mac
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_0) AppleWebKit/537.36 (KHTML, like
Gecko) Chrome/537.36 (@c26c0312e940221c424c2730ef72be2c69ac1b67) Safari/537.36 n
w(0.14.7) DingTalk(3.1.0)

iphone
Mozilla/5.0 (iPhone; CPU iPhone OS 9_2_1 like Mac OS X) AppleWebKit/601.1.46 (KH
TML, like Gecko) Mobile/13D15 AliApp(DingTalk/3.0.0) com.laiwang.DingTalk/177155
0  Channel/201200 language/zh-Hans
"""

mobile_pattern = re.compile("mobile", re.I)
idevice = re.compile(r"(iPhone|iPad|iPod)", re.I)

def dingding_client_ua_middleware(get_response):
    def middleware(request):
        ua = request.META.get("HTTP_USER_AGENT", "")
        request.from_device = "browser"
        request.dingding = False
        request.mobile = mobile_pattern.search(ua) and True or False
        if ua.find("DingTalk") >= 0:
            request.dingding = True
            if ua.find("dingtalk-win") >= 0:
                request.from_device = "pc"
            elif ua.find("com.alibaba.android") >= 0 or idevice.search(ua):
                request.from_device = "mobile"
            else:
                request.from_device = "pc" #mac

        response = get_response(request)
        return response
    return middleware
