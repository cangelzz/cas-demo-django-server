from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from dingding.models import DingUser
from security.models import ACL
from django.contrib.admin import SimpleListFilter, FieldListFilter
from django import forms

from base.models import *



class BaseAdmin(admin.ModelAdmin):
    actions_on_top = True
    actions_on_bottom = True


class RootOUFilter(SimpleListFilter):
    title = "大部门"
    parameter_name = "root"

    def lookups(self, request, model_admin):
        return OU.objects.filter(parent__name="Root-Inc").values_list("id", "name")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(root_ou__id=self.value())
        else:
            return queryset


class ActiveProfileListFilter(admin.SimpleListFilter):
    title = "在职状态"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        return (
            (1, "在职"),
            (0, "离职")
        )

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(user__is_active=True)
        if self.value() == "0":
            return queryset.filter(user__is_active=False)


class ProfileAdmin(BaseAdmin):
    model = Profile

    def active(self):
        return self.user.is_active

    active.boolean = True
    active.short_description = "有效"

    list_display = ["user", "full_name", "display_name", "jobnumber", active, "department", "manager", "root_ou", "ou",
                    "extNumber", "mobile"]
    search_fields = ["display_name", "xingming", "user__username", "jobnumber", "ou__name", "department", "extNumber",
                     "mobile"]
    list_filter = [ActiveProfileListFilter, "department", RootOUFilter, ("manager", admin.RelatedOnlyFieldListFilter)]
    ordering = ["jobnumber"]


class DepartmentAdmin(admin.ModelAdmin):
    pass


class OUAdmin(BaseAdmin):
    list_display = ["name", "parent"]


# Re-register UserAdmin
admin.site.site_header = "Backend User Center"
admin.site.unregister(User)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(OU, OUAdmin)
