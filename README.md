# cas demo django server

## cas server

* edit hosts ```127.0.0.1 www.casdemo.com```
* execute ```python manage.py runserver 0.0.0.0:8000```
* `cas_callbacks.py` return user defined attributes
* `admin/admin` for admin page, test1/test1 (~ test5/test5) for normal user

## ldap auth

* check out at `casdemo.auth.ActiveDirectoryAuthenticationBackEnd`


## dingtalk

* `client.py` helper functions for dingtalk api
* `templates/dingding/` auto login for integration with dingding
