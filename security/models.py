import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_slug
from django.db.models.signals import post_save
from urllib.parse import urljoin
from django.db.models import Q
from jsonfield import JSONField


class Application(models.Model):
    class Meta:
        verbose_name = "应用"
        verbose_name_plural = "应用"
        ordering = ["order", "name"]
        permissions = [
            ("can_access_user_base_info", "访问用户基本信息"),
            ("can_access_user_detail_info", "访问用户详细信息"),
            ("can_access_user_security_info", "访问用户安全信息")
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="应用名")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="描述")
    url = models.URLField(blank=True, default="", verbose_name="网站地址")
    active = models.BooleanField(default=True, verbose_name="有效")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name="开发者", null=True, blank=True,
                              related_name="owned_applications")
    managers = models.ManyToManyField(User, verbose_name="管理员", blank=True, related_name="managed_applications")
    secret = models.UUIDField(default=uuid.uuid4, editable=False)
    order = models.PositiveSmallIntegerField(default=1, verbose_name="排序", help_text="数值越小，排序越前")
    view_permission = models.ForeignKey("Permission", verbose_name="可见权限", null=True, blank=True,
                                        help_text="空为对所有用户实行默认可见状态，否则仅对拥有该权限的用户可见", related_name="+")
    app_visibility = models.BooleanField(default=True, verbose_name="应用默认是否可见")
    perm_visibility = models.BooleanField(default=True, verbose_name="应用功能默认是否可用")

    def __str__(self):
        return self.name

    def short_id(self):
        return self.id.hex[:6]

    def has_permission(self, user):
        from .utils import get_permissions
        if not self.view_permission:
            return self.app_visibility
        return get_permissions(user, self).filter(id=self.view_permission.id).exists()

    def root_functions(self, user=None):
        functions = Function.objects.filter(application=self, parent__isnull=True).order_by("order")
        if not user:
            return functions

        from .utils import get_permissions
        return functions.filter(Q(view_permission__isnull=True) | Q(view_permission__in=get_permissions(user, self)))

    def can_manage(self, user):
        return self.owner == user or self.managers.filter(id=user.id).exists() or user.is_superuser

    def get_display_name(self):
        return self.description or self.name

    def valid_acls(self):
        return (ACL.objects.filter(roles__application=self) | ACL.objects.filter(permissions__application=self)).filter(
            user__is_active=True).distinct().order_by("user__profile__xingming")


class ApplicationAlias(models.Model):
    application = models.ForeignKey(Application, verbose_name="应用")
    name = models.CharField(max_length=50, verbose_name="别名", unique=True, db_index=True)

    class Meta:
        verbose_name = "应用假名"
        verbose_name_plural = "应用假名"

    def __str__(self):
        return self.name + " : " + self.application.name


class Permission(models.Model):
    class Meta:
        verbose_name = "权限"
        verbose_name_plural = "权限"
        ordering = ["application", "name"]
        unique_together = ["application", "name"]
        index_together = ["application", "name"]

    application = models.ForeignKey(Application, related_name="permissions", verbose_name="应用")
    name = models.CharField(max_length=200, db_index=True, verbose_name="权限名", help_text="请使用英文")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="权限描述", help_text="中文名称")
    comment = models.TextField(verbose_name="备注", null=True, blank=True)

    def __str__(self):
        return "%s:%s" % (self.application, self.name)

    def get_display_name(self):
        return self.description or self.name

    @property
    def sorted_acls(self):
        return self.assigned_acls.order_by("user__profile__xingming")

    def granted_acls(self):
        acls = self.assigned_acls.all()
        for role in self.roles.all():
            acls |= role.assigned_acls.all()

        acls = acls.distinct()
        return acls

    def inherited_acls(self):
        acls = ACL.objects.none()
        for role in self.roles.all():
            acls |= role.assigned_acls.all()

        acls = acls.distinct().order_by("user__profile__xingming")
        return acls


class AppUrl(models.Model):
    class Meta:
        verbose_name = "路径"
        verbose_name_plural = "路径"
        ordering = ["application", "url"]
        unique_together = ["application", "url"]

    application = models.ForeignKey(Application, verbose_name="应用")
    description = models.CharField(max_length=50, verbose_name="描述")
    url = models.CharField(max_length=500, verbose_name="URL")

    def __str__(self):
        return urljoin(self.application.url, self.url)


class Role(models.Model):
    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        ordering = ["application", "name"]
        unique_together = ["application", "name"]
        index_together = ["application", "name"]

    application = models.ForeignKey(Application, related_name="roles", verbose_name="应用")
    name = models.CharField(max_length=200, db_index=True, verbose_name="角色名", help_text="请使用英文")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="角色中文描述", help_text="请使用中文，不建议太长")
    comment = models.TextField(verbose_name="备注", null=True, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True, verbose_name="角色拥有权限")
    urls = models.ManyToManyField(AppUrl, related_name="roles", blank=True, verbose_name="角色可访问的URL")

    def __str__(self):
        return "%s:%s" % (self.application, self.name)

    def get_display_name(self):
        return self.description or self.name

    @property
    def sorted_acls(self):
        return self.assigned_acls.order_by("user__profile__xingming")


class ACL(models.Model):
    class Meta:
        verbose_name = "访问控制项"
        verbose_name_plural = "访问控制表"

    user = models.OneToOneField(User, verbose_name="域账户", editable=False)
    roles = models.ManyToManyField(Role, blank=True, related_name="assigned_acls", verbose_name="角色")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="assigned_acls", verbose_name="权限")
    urls = models.ManyToManyField(AppUrl, blank=True, related_name="assigned_urls", verbose_name="路径")

    def __str__(self):
        return self.user.profile.fullname()


class Property(models.Model):
    acl = models.ForeignKey(ACL, related_name="properties", verbose_name="属性")
    application = models.ForeignKey(Application, verbose_name="应用")
    content = JSONField(verbose_name="自定义内容", null=True, blank=True, default={})
    created = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    class Meta:
        verbose_name = "属性"
        verbose_name_plural = "属性"
        unique_together = [("acl", "application")]


class Function(models.Model):
    class Meta:
        verbose_name = "应用功能"
        verbose_name_plural = "应用功能（菜单）"
        unique_together = [("application", "name"), ("application", "slug")]
        ordering = ["application", "order"]

    application = models.ForeignKey(Application, related_name="functions", verbose_name="应用")
    name = models.CharField(max_length=50, verbose_name="功能名称")
    slug = models.SlugField(max_length=50, verbose_name="英文名称")
    path = models.CharField(max_length=1024, verbose_name="功能路径")
    view_permission = models.ForeignKey(Permission, verbose_name="对应权限", null=True, blank=True,
                                        help_text="空为对所有用户实行默认可见状态，否则仅对拥有该权限的用户可见", related_name="+")
    order = models.PositiveSmallIntegerField(default=1, verbose_name="排序", help_text="数字越小，排序越前")
    folder = models.BooleanField(default=False, verbose_name="是否是目录")
    parent = models.ForeignKey('self', null=True, blank=True, verbose_name="上级")

    def __str__(self):
        return "%s: %s" % (self.application.description, self.name)

    def full_path(self):
        if self.path.startswith("http") or self.path.startswith("//"):
            return self.path
        return urljoin(self.application.url, self.path)

    def has_permission(self, user):
        from .utils import get_permissions
        if not self.view_permission:
            return self.application.perm_visibility
        return get_permissions(user, self).filter(id=self.view_permission.id).exists()

    def sub_functions(self, user=None):
        functions = self.function_set.order_by("order")
        if not user:
            return functions

        from .utils import get_permissions
        return functions.filter(Q(view_permission__isnull=True) | Q(view_permission__in=get_permissions(user, self.application)))