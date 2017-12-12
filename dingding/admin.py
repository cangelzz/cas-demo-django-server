from django.contrib import admin
from dingding.models import *
from base.admin import BaseAdmin
from django.utils.safestring import mark_safe

class DingUserAdmin(BaseAdmin):
    def binded(self):
        return self.user_id and True or False

    ordering = ["aduser__username"]
    binded.boolean = True
    binded.short_description = "绑定状态"
    list_display = list(admin.ModelAdmin.list_display) + ["aduser", binded, "user_id"]
    search_fields = ["aduser__username"]


class ApplicationInline(admin.StackedInline):
    model = Application
    can_delete = True
    extra = 0


class CompanyAdmin(BaseAdmin):
    def apps(self):
        a = []
        for app in self.application_set.all():
            a.append("%d: %s: %s" % (app.id, app.name, app.agent_id))
        return mark_safe("<br>".join(a))

    list_display = ["name", "corp_id", "corp_secret", apps]
    inlines = [ApplicationInline]

admin.site.register(DingUser, DingUserAdmin)
admin.site.register(Company, CompanyAdmin)
