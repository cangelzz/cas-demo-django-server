import logging
from ldap3 import Server, Connection, NTLM, SUBTREE
from ldap3.core.exceptions import LDAPBindError
from base.ldap import USER_BASE_DN
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from axes.decorators import get_ip

logger = logging.getLogger(__name__)


class ActiveDirectoryAuthenticationBackEnd:
    def __init__(self):
        pass

    def authenticate(self, username, password, request=None):
        request_info = request and "%s %s" % (request.path, get_ip(request)) or ""
        if not username or not password:
            logger.info("Log In Failure [Empty] %s %s" % (username, request_info))
            return None
        try:
            server = Server(settings.AD_SERVER_NAME, use_ssl=True)
            conn = Connection(server, "%s\\%s" % (settings.AD_DOMAIN, username), password, auto_bind=True,
                              authentication=NTLM)
            user = conn.bound and self.get_or_create_user(username, conn) or None
            if user is not None:
                pass
            else:
                logger.info("Log In Failure [NOTFOUND] %s %s" % (username, request_info))
            return user
        except LDAPBindError:
            logger.info("Log In Failure [LDAP] %s %s" % (username, request_info))
            return None


    def get_or_create_user(self, username, conn=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if conn is None:
                return None

            if conn.search(USER_BASE_DN, "(sAMAccountName=%s)" % username, SUBTREE, attributes=["sn", "givenName"]):
                result = conn.response[0]["attributes"]
                user = User(username=username, password="testtest")
                user.first_name = result["givenName"]
                user.last_name = result["sn"]
                user.email = "%s@%s" % (username, settings.AD_EMAIL_HOST)
                user.save()
            else:
                logger.warning("user not found in AD")
                return None
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


def post_logged_in(sender, request, user, **kwargs):
    request_info = "%s %s" % (request.path, get_ip(request))
    logger.info("Log In Success %s %s" % (user.username, request_info))


def post_logged_out(sender, request, user, **kwargs):
    request_info = "%s %s" % (request.path, get_ip(request))
    logger.info("Log Out %s %s" % (user and user.username or "none", request_info))


def post_login_failed(sender, request, credentials, **kwargs):
    request_info = "%s %s" % (request.path, get_ip(request))
    logger.info("Signal Log In Failure %s %s" % (credentials.get("username", "-"), request_info))


user_logged_in.connect(post_logged_in)
user_logged_out.connect(post_logged_out)
user_login_failed.connect(post_login_failed)
