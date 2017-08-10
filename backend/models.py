from django.db import models


# Create your models here.
class PhoneDevice(models.Model):
    """
    手机
    """
    label = models.CharField(max_length=50)
    type = models.IntegerField("类型", default=1, help_text="0 - 手机，1 - 虚拟机")
    model = models.CharField(max_length=20)
    system = models.CharField(max_length=50)
    status = models.IntegerField(default=0)
    owner = models.ForeignKey(User, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class User(models.Model):
    """
    用户
    """
    name = models.CharField(max_length=30)
    email = models.CharField(max_length=30)
    status = models.IntegerField(default=0)


class App(models.Model):
    """
    生活圈
    """
    app_id = models.IntegerField(primary_key=True)
    app_name = models.CharField(max_length=32)


class AppUser(models.Model):
    """
    生活圈用户
    """
    name = models.CharField(max_length=30)
    user_id = models.IntegerField()
    memo = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)


class SnsUser(models.Model):
    """
    微信/QQ用户
    """
    name = models.CharField(max_length=30)
    type = models.IntegerField()
    login_name = models.CharField(max_length=30)
    passwd = models.CharField(max_length=30)
    status = models.IntegerField(default=0)
    memo = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=30)
    device = models.ForeignKey(PhoneDevice, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, null=True)
    app = models.ForeignKey(App)


class SnsGroup(models.Model):
    """
    qq／微信群
    """
    group_id = models.CharField(max_length=50, primary_key=True)
    type = models.IntegerField(default=0)
    group_name = models.CharField(50)
    group_user_count = models.IntegerField(default=0)
    status = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class SnsUserGroup(models.Model):
    """
    用户群
    """
    sns_user = models.ForeignKey(SnsUser)
    sns_group = models.ForeignKey(SnsGroup)
    nick_name = models.CharField(50)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)
    active = models.IntegerField(default=0)
    last_post_at = models.DateTimeField(null=True)


class UserActionLog(models.Model):
    """
    用户操作历史
    """
    user = models.ForeignKey(User)
    action = models.CharField(max_length=20)

    memo = models.CharField(max_length=255)
    action_time = models.DateTimeField(auto_now_add=True)
