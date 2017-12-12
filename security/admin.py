from .models import *
from .utils import get_user_applications
from base.admin import BaseAdmin
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.db.models import F
from django.template.loader import render_to_string
from urllib.parse import urljoin

LIMIT_ADMIN = False


class ApplicationAdmin(BaseAdmin):
    def users_count(self):
        return ACL.objects.filter(Q(roles__application=self) | Q(permissions__application=self)).distinct().count()

    def name(self):
        if not self.owner:
            return "-"
        return self.owner.profile.fullname()

    def managers(self):
        return " ".join(list(self.managers.values_list("profile__full_name", flat=True)))

    name.short_description = "开发者"
    users_count.short_description = "用户数"
    list_display = ["name", "description", "url", "active", users_count, name, managers, "view_permission"]
    fields = ["id", "secret", "owner", "name", "description", "url", "view_permission", "active",
              "app_visibility", "perm_visibility"]
    filter_horizontal = ["managers"]
    readonly_fields = ["id", "secret"]
    list_filter = [("owner", admin.RelatedOnlyFieldListFilter)]

    def get_fields(self, request, obj=None):
        fields = super(ApplicationAdmin, self).get_fields(request, obj)
        if request.user.is_superuser and not LIMIT_ADMIN or (obj and obj.owner or None == request.user):
            if "managers" not in fields:
                fields.insert(5, "managers")
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = super(ApplicationAdmin, self).get_readonly_fields(request, obj)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return fields
        else:
            return fields + ["owner"]

    def get_queryset(self, request):
        qs = super(ApplicationAdmin, self).get_queryset(request)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return qs

        return get_user_applications(request.user)

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
        super(ApplicationAdmin, self).save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.object_id = object_id
        return super(ApplicationAdmin, self).change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "view_permission":
            if getattr(self, "object_id", None):
                kwargs["queryset"] = Permission.objects.filter(application__id=self.object_id)

        return super(ApplicationAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ApplicationAliasAdmin(BaseAdmin):
    list_display = ["application", "name"]
    list_filter = [("application", admin.RelatedOnlyFieldListFilter)]


class PermissionAdmin(BaseAdmin):
    def users(self):
        return " ".join(list(self.users.values_list("profile__full_name", flat=True)))

    def user_count(self):
        qs = self.assigned_acls.all()
        for r in self.roles.all():
            qs = qs | r.assigned_acls.all()

        qs = qs.distinct()
        cnt = qs.count()
        if cnt:
            return "%d: %s" % (cnt, " ".join(qs.values_list("user__profile__full_name", flat=True)))

    user_count.short_description = "授权用户"

    list_display = ["application", "name", "description", user_count]
    list_filter = ["application__name"]
    search_fields = ["name", "description"]

    def get_queryset(self, request):
        qs = super(PermissionAdmin, self).get_queryset(request)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return qs

        return qs.filter(application__in=get_user_applications(request.user))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.object_id = object_id
        return super(PermissionAdmin, self).change_view(request, object_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "application":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = get_user_applications(request.user)

        return super(PermissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class AppUrlAdmin(BaseAdmin):
    def full_url(self):
        return urljoin(self.application.url, self.url)

    list_display = [full_url, "description"]
    full_url.short_description = "完整路径"

    list_filter = [("application", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["url", "description"]

    def get_queryset(self, request):
        qs = super(AppUrlAdmin, self).get_queryset(request)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return qs

        return qs.filter(application__in=get_user_applications(request.user))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "application":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = get_user_applications(request.user)

        return super(AppUrlAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class RoleAdmin(BaseAdmin):
    def users(self):
        qs = self.assigned_acls.all()
        cnt = qs.count()
        if cnt:
            return "%d: %s" % (
                cnt, " ".join(list(self.assigned_acls.values_list("user__profile__full_name", flat=True))))

    users.short_description = "授权用户"

    list_display = ["application", "name", "description", users]
    list_filter = [("application", admin.RelatedOnlyFieldListFilter)]
    filter_horizontal = ["permissions", "urls"]
    search_fields = ["name", "description"]

    def get_queryset(self, request):
        qs = super(RoleAdmin, self).get_queryset(request)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return qs

        return qs.filter(application__in=get_user_applications(request.user))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.role = Role.objects.get(id=object_id)
        return super(RoleAdmin, self).change_view(request, object_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "application":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = get_user_applications(request.user)

        return super(RoleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            if getattr(self, "role", None):
                kwargs["queryset"] = Permission.objects.filter(application=self.role.application)
            else:
                kwargs["queryset"] = Permission.objects.filter(application__in=get_user_applications(request.user))

        if db_field.name == "urls":
            if getattr(self, "role", None):
                kwargs["queryset"] = AppUrl.objects.filter(application=self.role.application)
            else:
                kwargs["queryset"] = AppUrl.objects.filter(application__in=get_user_applications(request.user))

        return super(RoleAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class ApplicationListFilter(admin.SimpleListFilter):
    title = "应用"

    parameter_name = "app"

    def lookups(self, request, model_admin):
        return get_user_applications(request.user).values_list("id", "name")

    def queryset(self, request, queryset):
        if self.value():
            application = Application.objects.get(id=self.value())
            return queryset.filter(Q(roles__application=application) | Q(permissions__application=application))


class ACLAdmin(BaseAdmin):
    def user_roles(self):
        # return mark_safe(
        #    "<br>".join(["%s:%s" % (a, r) for a, r in
        #                 self.roles.annotate(display=F("description")).values_list("application__name", "display")]))
        items = self.roles.select_related()
        return mark_safe(render_to_string("security/includes/admin_acl_list.html", {"items": items}))

    def user_permissions(self):
        items = self.permissions.select_related()
        return mark_safe(render_to_string("security/includes/admin_acl_list.html", {"items": items}))

    def user_name(self):
        return self.user.profile.display_name or self.user.username

    search_fields = ["user__username", "user__profile__full_name"]
    filter_horizontal = ["roles", "permissions"]
    list_display = [user_name, user_roles, user_permissions]
    list_filter = [ApplicationListFilter]
    ordering = ["user__profile__xingming"]
    exclude = ["urls"]
    user_name.short_description = "用户"
    user_roles.short_description = "拥有角色"
    user_permissions.short_description = "拥有权限"

    def formfield_for_manytomany(self, db_field, request, **kwargs):

        if db_field.name == "roles":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = Role.objects.filter(application__in=get_user_applications(request.user))

        if db_field.name == "permissions":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = Permission.objects.filter(application__in=get_user_applications(request.user))

        return super(ACLAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


class PropertyAdmin(BaseAdmin):
    def acl_username(self):
        return self.acl.user.profile.full_name

    acl_username.short_description = "用户"

    def application(self):
        return self.application.get_display_name()

    application.short_description = "应用"

    list_display = [acl_username, application, "updated"]
    list_filter = [("application", admin.RelatedOnlyFieldListFilter), ("acl", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["acl__user__username", "acl__user__profile__full_name", "application__name", "application__description"]
    ordering = ["-updated"]


class FunctionAdmin(BaseAdmin):
    list_display = ["application", "name", "path", "view_permission", "order"]
    search_fields = ["name", "path"]
    ordering = ["application"]
    list_filter = ["application__name"]

    def get_queryset(self, request):
        qs = super(FunctionAdmin, self).get_queryset(request)
        if request.user.is_superuser and not LIMIT_ADMIN:
            return qs

        return qs.filter(application__in=get_user_applications(request.user))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.function = Function.objects.get(id=object_id)
        return super(FunctionAdmin, self).change_view(request, object_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "application":
            if request.user.is_superuser and not LIMIT_ADMIN:
                pass
            else:
                kwargs["queryset"] = get_user_applications(request.user)

        if db_field.name == "view_permission":
            if hasattr(self, "function"):
                kwargs["queryset"] = Permission.objects.filter(application=self.function.application)
            else:
                kwargs["queryset"] = Permission.objects.filter(application__in=get_user_applications(request.user))

        if db_field.name == "parent":
            if hasattr(self, "function"):
                kwargs["queryset"] = Function.objects.filter(application=self.function.application, folder=True)
            else:
                kwargs["queryset"] = Function.objects.filter(application__in=get_user_applications(request.user),
                                                             folder=True)

        return super(FunctionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Application, ApplicationAdmin)
admin.site.register(ApplicationAlias, ApplicationAliasAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(AppUrl, AppUrlAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(ACL, ACLAdmin)
admin.site.register(Property, PropertyAdmin)
admin.site.register(Function, FunctionAdmin)
