from django import template
from dingding.client import ClientWrapper

register = template.Library()


@register.inclusion_tag("dingding/config.html")
def ding_config(request):
    client = ClientWrapper("portal")
    url = request.build_absolute_uri()
    data = client.get_request_signature(url)
    data["agent_id"] = client.corpinfo["config"][2]
    data["corp_id"] = client.corpinfo["config"][0]
    return data
