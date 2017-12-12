import re
from ldap3 import Server, Connection, SUBTREE, NTLM, BASE, LEVEL
from ldap3.core.exceptions import LDAPBindError, LDAPAttributeError
from ldap3.extend.microsoft import modifyPassword, unlockAccount
import getpass
from django.conf import settings
import ssl

USER_BASE_DN = "OU=Test,DC=Test,DC=com"
USER_CATEGORY_DN = "CN=Person,CN=Schema,CN=Configuration,DC=Test,DC=com"
OU_CATEGORY_DN = "CN=Organizational-Unit,CN=Schema,CN=Configuration,DC=test,DC=com"


def guid2str(val):
    import uuid
    return uuid.UUID(bytes_le=val).hex

class LdapServer(object):
    """
    示例代码，根据实际情况进行改写
    """
    def __init__(self, **options):
        username = options.get("username", None)
        password = options.get("password", None)
        use_ssl = options.get("use_ssl", False)
        server_name = options.get("server", settings.AD_SERVER_NAME)
        if not username:
            username = input("Enter username: ").strip()

        if not password:
            password = getpass.getpass("Enter password for %s: " % username).strip()

        try:
            server = Server(settings.AD_SERVER_NAME_WRITE, use_ssl=use_ssl)
            conn = Connection(server, "%s\\%s" % (settings.AD_DOMAIN, username), password, auto_bind=True,
                              authentication=NTLM)
            self.conn = conn.bound and conn or None
        except LDAPBindError:
            print("error, wrong password")
            self.conn = None

    def search_user(self, username):
        if self.conn is None:
            return None

        result = self._search(USER_BASE_DN, "(sAMAccountName=%s)" % username, SUBTREE, attributes=["sn", "givenName"])
        for user in result:
            user["username"] = username
            user["email"] = "%s@%s" % (username, settings.AD_EMAIL_HOST)

        return result

    def get_user(self, username, attributes=["sn", "givenName"], base_dn=USER_BASE_DN):
        if self.conn is None:
            return None

        result = self._search(base_dn, "(sAMAccountName=%s)" % username, SUBTREE, attributes=attributes)
        cnt = len(result)
        if not cnt:
            return None

        return result[0]

    def _search(self, dn, cond, scope, attributes):
        if self.conn is None:
            return None

        if self.conn.search(dn, cond, scope, attributes=attributes):
            result = []
            for entry in self.conn.entries:
                item = {}
                for attr in attributes:
                    item[attr] = self._get(entry, attr)
                result.append(item)

            return result

        return []

    def _get(self, result, key):
        try:
            return getattr(result, key).value
        except LDAPAttributeError:
            return ""
        except:
            return ""


class NoConnectionException(Exception):
    pass


class FailedConnectionException(Exception):
    pass