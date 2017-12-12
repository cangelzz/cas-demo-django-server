# cas demo django server

## cas server

* edit hosts ```127.0.0.1 www.casdemo.com```
* execute ```python manage.py runserver 0.0.0.0:8000```
* `cas_callbacks.py` return user defined attributes

## ldap auth

* check out `casdemo.auth.ActiveDirectoryAuthenticationBackEnd`


## dingtalk

* `client.py` helper functions for dingtalk api
* `templates/dingding/` auto login for integration with dingding
