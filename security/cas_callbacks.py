from .utils import get_roles, get_permissions, get_urls, get_properties
import re
from .models import Application, ApplicationAlias

pattern = re.compile(r"http[s]?://([\w:-]+)(\.casdemo.com)?")

def user_security_attributes(user, service):
    """Return all available user name related fields and methods."""
    application = None
    m = pattern.search(service)
    if m:
        app_name = m.group(1)
        try:
            application = Application.objects.get(name=app_name)
        except Application.DoesNotExist:
            try:
                alias = ApplicationAlias.objects.get(name=app_name)
                application = alias.application
            except ApplicationAlias.DoesNotExist:
                pass

    attributes = {}
    attributes["service"] = service
    attributes["app_name"] = application and application.name or ""
    attributes["app_id"] = application and application.id.hex or ""
    attributes["roles.list"] = get_roles(user, application, type="list")
    attributes["permissions.list"] = get_permissions(user, application, type="list")
    attributes["urls.list"] = get_urls(user, application, type="list")
    attributes["properties"] = get_properties(user, application, type="dict")
    return attributes
