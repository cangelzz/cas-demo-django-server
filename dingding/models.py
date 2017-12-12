from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core.validators import validate_slug
from django.contrib.sites.shortcuts import get_current_site


class DingUser(models.Model):
    class Meta:
        verbose_name = "钉钉帐号"
        verbose_name_plural = "钉钉帐号"

    aduser = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="域账户")
    name = models.CharField(max_length=50, null=True, blank=True, verbose_name="姓名")
    avatar = models.URLField(null=True, blank=True, verbose_name="头像")
    ding_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="全局用户ID")
    user_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="企业用户ID")
    mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name="手机号")

    def __str__(self):
        return self.aduser.profile.fullname()

    def get_avatar(self):
        avatar = (self.avatar in ["", "undefined"] or self.avatar is None) and "/static/anonymouse.png" or self.avatar
        avatar = avatar.replace("http:", "")
        return avatar

    def get_absolute_avatar(self):
        avatar = (self.avatar in ["", "undefined"] or self.avatar is None) and "//%s/static/anonymouse.png" % get_current_site(None).domain or self.avatar
        avatar = avatar.replace("http:", "")
        return avatar

    @property
    def avatar_url(self):
        if self.avatar is None or self.avatar in ["", "undefined"]:
            return None
        else:
            return self.avatar.replace("http://", "https://")


def create_ding_user(sender, instance, created, **kwargs):
    DingUser.objects.get_or_create(aduser=instance)


post_save.connect(create_ding_user, sender=User)


class ChatGroup(models.Model):
    class Meta:
        verbose_name = "钉钉群"
        verbose_name_plural = "钉钉群"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ownedchatgroups", verbose_name="群主")
    name = models.CharField(max_length=20, validators=[validate_slug], unique=True, db_index=True, verbose_name="群名称")
    description = models.CharField(max_length=100, blank=True, default="", verbose_name="描述")
    chat_id = models.CharField(max_length=100, blank=True, default="", verbose_name="群ID")
    users = models.ManyToManyField(User, related_name="chatgroups", verbose_name="群成员")

    def __str__(self):
        return "%s %s %s %s" % (self.description, self.name, self.owner.profile.fullname(), self.chat_id)


class Company(models.Model):
    class Meta:
        verbose_name = "钉钉企业"
        verbose_name_plural = "钉钉企业"

    name = models.CharField(max_length=10, unique=True, validators=[validate_slug], verbose_name="企业名称")
    description = models.CharField(max_length=100, null=True, blank=True, verbose_name="企业描述")
    corp_id = models.CharField(max_length=32, verbose_name="Corp ID")
    corp_secret = models.CharField(max_length=64, verbose_name="Corp Secret")

    def __str__(self):
        return self.name


class Application(models.Model):
    class Meta:
        verbose_name = "钉钉应用"
        verbose_name_plural = "钉钉应用"
        unique_together = [("company", "name"), ("company", "agent_id")]

    company = models.ForeignKey(Company, verbose_name="企业")
    name = models.CharField(unique=True, max_length=10, validators=[validate_slug], verbose_name="应用名称")
    description = models.CharField(max_length=100, verbose_name="应用描述")
    agent_id = models.IntegerField(verbose_name="Agent ID")

    def __str__(self):
        return "%s: %s" % (self.company, self.name)
