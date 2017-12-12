from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from uuslug import slugify


def myslugify(s):
    return slugify(s).replace("-", "")


class Tag(models.Model):
    class Meta:
        verbose_name = "用户标签"
        verbose_name_plural = "用户标签"

    text = models.CharField(max_length=50, verbose_name="标签", unique=True)

    def __str__(self):
        return self.text


class Profile(models.Model):
    class Meta:
        verbose_name = "用户信息"
        verbose_name_plural = "用户信息"
        ordering = ["order", "xingming"]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="域账户")
    display_name = models.CharField(max_length=50, blank=True, null=True, default="", verbose_name="全名")
    full_name = models.CharField(max_length=50, blank=True, null=True, default="", verbose_name="姓名")
    xing = models.SlugField(default="a", verbose_name="英文姓")
    ming = models.SlugField(default="a", verbose_name="英文名")
    xingming = models.SlugField(default="a", verbose_name="英文姓名")
    jobnumber = models.CharField(max_length=6, blank=True, default="", verbose_name="工号")
    extNumber = models.CharField(max_length=4, blank=True, null=True, default="", verbose_name="分机号")
    mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name="手机号")
    department = models.CharField(max_length=50, blank=True, null=True, default="", verbose_name="部门")
    ou = models.ForeignKey('OU', null=True, on_delete=models.SET_NULL, verbose_name="AD部门",
                           related_name="direct_profiles", blank=True)
    dn = models.CharField(max_length=255, verbose_name='DN', null=True, blank=True)
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="上级经理")
    root_ou = models.ForeignKey('OU', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="大部门",
                                related_name="all_profiles")
    order = models.PositiveIntegerField(default=99999, verbose_name="排序")

    def fullname(self):
        return self.user.first_name is not "" and "%s%s" % (
            self.user.last_name, self.user.first_name) or self.user.username

    def __str__(self):
        return self.fullname()

    def save(self, *args, **kwargs):
        user = self.user
        if not self.id:
            self.xing = myslugify(user.last_name)
            self.ming = myslugify(user.first_name)
            self.xingming = "%s%s" % (self.xing, self.ming)
        super(Profile, self).save(*args, **kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=User)


class Department(models.Model):
    class Meta:
        verbose_name = "部门"
        verbose_name_plural = "部门"

    name = models.CharField(max_length=50, unique=True, verbose_name="部门名称")

    def __str__(self):
        return self.name


class OU(models.Model):
    class Meta:
        verbose_name = "AD部门"
        verbose_name_plural = "AD部门"
        ordering = ["order", "name"]

    guid = models.CharField(max_length=32, unique=True, verbose_name="GUID")
    dn = models.CharField(max_length=255, unique=True, verbose_name="DN")
    name = models.CharField(max_length=20, verbose_name="部门名称")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, verbose_name="上级部门")
    order = models.PositiveIntegerField(default=0, verbose_name="排序")
    hidden = models.BooleanField(default=False, verbose_name="隐藏")

    def __str__(self):
        return self.name

    def get_root(self):
        ou = self
        while ou.parent and ou.parent.name != "Root-Inc":
            ou = ou.parent

        return ou

    def all_profiles_active(self):
        return self.all_profiles.filter(user__is_active=True)

    def direct_profiles_active(self):
        return self.direct_profiles.filter(user__is_active=True)
