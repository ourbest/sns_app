from django.db import models


class App(models.Model):
    """
    生活圈
    """
    app_id = models.IntegerField('ID', primary_key=True)
    app_name = models.CharField('名称', max_length=32)
    stage = models.CharField('所处时期', max_length=20, default='准备期')
    self_qun = models.IntegerField('自行导入群', default=1)

    def __str__(self):
        return '%s (%s)' % (self.app_name, self.app_id)

    class Meta:
        verbose_name = '生活圈'
        verbose_name_plural = ' 生活圈列表'


class User(models.Model):
    """
    用户
    """
    name = models.CharField('姓名', max_length=30)
    email = models.CharField('邮箱', max_length=50)
    status = models.IntegerField('状态', default=0)
    passwd = models.CharField('密码', max_length=50)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    role = models.IntegerField(default=0, help_text='0-组员 1-组长')
    app = models.ForeignKey(App, verbose_name='生活圈', null=True, blank=True, default=None)
    phone = models.CharField(max_length=20, help_text='手机号', null=True, blank=True)
    notify = models.IntegerField(default=0, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '员工'
        verbose_name_plural = ' 员工列表'


class UserAuthApp(models.Model):
    """
    用户授权的APP列表
    """
    user = models.ForeignKey(User)
    app = models.ForeignKey(App)


# Create your models here.
class PhoneDevice(models.Model):
    """
    手机
    """
    label = models.CharField('编号', max_length=50)
    phone_num = models.CharField('手机号', max_length=20)
    type = models.IntegerField("类型", default=0, help_text="0 - 手机，1 - 虚拟机")
    model = models.CharField('型号', max_length=20, null=True, blank=True)
    system = models.CharField('系统和版本', max_length=50, null=True, blank=True)
    status = models.IntegerField('状态', default=0)
    owner = models.ForeignKey(User, null=True, blank=True, verbose_name='所有者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    memo = models.CharField('备注', null=True, blank=True, max_length=50)

    @property
    def friend_text(self):
        return '%s%s' % (self.label, '' if not self.memo else '(%s)' % self.memo)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = '手机'
        verbose_name_plural = ' 手机列表'


class AppUser(models.Model):
    """
    生活圈马甲用户
    """
    name = models.CharField('名字', max_length=30)
    type = models.IntegerField('类型', help_text='0:qq分享 1:微信分享 2:其他', default=0)
    cutt_user_id = models.BigIntegerField('生活圈用户ID')
    memo = models.CharField('备注', max_length=50)
    created_at = models.DateTimeField('添加时间', auto_now_add=True)
    user = models.ForeignKey(User, verbose_name='属于')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'APP马甲'
        verbose_name_plural = ' APP马甲列表'


class SnsUser(models.Model):
    """
    微信/QQ用户
    """
    name = models.CharField('显示名', max_length=30)
    type = models.IntegerField('类型', default=0, help_text='0 - QQ 1 - 微信')
    login_name = models.CharField('登录名', max_length=80)
    passwd = models.CharField('密码', max_length=30)
    status = models.IntegerField('状态', default=0)
    memo = models.CharField('备注', max_length=255, null=True, blank=True)
    phone = models.CharField('电话', max_length=30)
    device = models.ForeignKey(PhoneDevice, null=True, verbose_name='设备')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    owner = models.ForeignKey(User, null=True, verbose_name='所有者')
    app = models.ForeignKey(App, verbose_name='生活圈')
    bot_login_token = models.BinaryField(null=True, blank=True)
    dist = models.IntegerField(default=1)
    friend = models.IntegerField(default=1)
    search = models.IntegerField(default=0)
    provider = models.CharField(default='qq', max_length=10)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '社交账号'
        verbose_name_plural = ' 社交账号列表'


class SnsGroup(models.Model):
    """
    qq／微信群
    """
    group_id = models.CharField('群ID', max_length=80, primary_key=True)
    type = models.IntegerField('类型', default=0, help_text='0 - QQ 1 - 微信')
    group_name = models.CharField('群名', max_length=50)
    group_user_count = models.IntegerField('群用户数', default=0)
    status = models.IntegerField('状态', default=0, help_text='0 - 未使用 1 - 已分配 -1 - 忽略')
    app = models.ForeignKey(App, verbose_name='生活圈', null=True)
    created_at = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)
    quiz = models.CharField(verbose_name='问题答案', max_length=50, null=True, blank=True)
    from_user = models.ForeignKey(User, verbose_name='爬群用户', null=True, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.group_name, self.group_id)

    class Meta:
        verbose_name = '群'
        verbose_name_plural = '群列表'


class SnsUserGroup(models.Model):
    """
    用户群
    """
    sns_user = models.ForeignKey(SnsUser, verbose_name='用户')
    sns_group = models.ForeignKey(SnsGroup, verbose_name='群')
    nick_name = models.CharField(max_length=50, verbose_name='备注名', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    status = models.IntegerField(default=0, verbose_name='状态')
    active = models.IntegerField(default=0, verbose_name='可用')
    last_post_at = models.DateTimeField(null=True, verbose_name='最后分发时间')

    def __str__(self):
        return str(self.sns_group)

    class Meta:
        unique_together = ('sns_group', 'sns_user')


class SnsUserInfo(models.Model):
    """
    用户信息
    """
    type = models.IntegerField(default=0, help_text="0 - QQ 1 - 微信")
    uin = models.CharField(max_length=50)
    user_id = models.CharField(max_length=50)
    nick = models.CharField(max_length=100)
    avatar = models.CharField(max_length=255)
    memo = models.CharField(max_length=255)

    def __str__(self):
        return '%s (%s)' % (self.nick, self.user_id)


class SnsGroupUser(models.Model):
    """
    群中的用户信息
    """
    group = models.ForeignKey(SnsGroup, verbose_name='群')
    user = models.ForeignKey(SnsUserInfo, verbose_name='用户')
    nick = models.CharField('昵称', max_length=50)
    title = models.CharField('头衔', max_length=20)
    created_at = models.DateTimeField('添加时间', auto_now_add=True)
    status = models.IntegerField('状态', default=0)
    updated_at = models.DateTimeField('修改时间', auto_now=True)

    def __str__(self):
        return str(self.user)


class SnsGroupSplit(models.Model):
    """
    推广人员分配到的群表
    """
    group = models.ForeignKey(SnsGroup, verbose_name='群')
    user = models.ForeignKey(User, verbose_name='推广人')
    status = models.IntegerField('状态', default=0, help_text='0 默认 1 已发送 2 已申请 3 已通过 -1 忽略')
    created_at = models.DateTimeField('添加时间', auto_now_add=True)
    updated_at = models.DateTimeField('修改时间', auto_now=True, null=True)
    phone = models.ForeignKey(PhoneDevice, null=True, verbose_name='设备')


#
# class SnsGroupApply(models.Model):
#     """
#     加群记录
#     """
#     group_split = models.ForeignKey(SnsGroupSplit, verbose_name='分配')
#     task = models.ForeignKey(SnsTaskDevice)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     sns_user = models.ForeignKey(SnsUser)
#     status = models.IntegerField(default=0)
#

class SnsGroupLost(models.Model):
    """
    丢失的群列表
    """
    group = models.ForeignKey(SnsGroup, verbose_name='群')
    sns_user = models.ForeignKey(SnsUser, verbose_name='账号')
    status = models.IntegerField('状态', default=0, help_text='0 - 未处理, 1 - 已处理')
    created_at = models.DateTimeField('添加时间', auto_now_add=True)


class SnsTaskType(models.Model):
    """
    任务类型
    """
    name = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    memo = models.CharField(max_length=255, null=True)


class ActiveDevice(models.Model):
    """
    当前在线的设备
    """
    device = models.ForeignKey(PhoneDevice, verbose_name='设备')
    active_at = models.DateTimeField('最后上线时间', auto_now=True)
    status = models.IntegerField('状态', default=0, help_text='0 - 正常， 1 - 工作中')


class DistArticle(models.Model):
    item_id = models.IntegerField(unique=True)
    app = models.ForeignKey(App)
    title = models.CharField(max_length=255)
    delete_flag = models.IntegerField(default=0)
    category = models.CharField(max_length=30, null=True, blank=True)
    created_at = models.DateTimeField()
    started_at = models.DateTimeField()


class SnsTask(models.Model):
    """
    任务
    """
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.ForeignKey(SnsTaskType)
    data = models.TextField(blank=True, null=True)
    status = models.IntegerField(default=0)
    app = models.ForeignKey(App, null=True)
    creator = models.ForeignKey(User, null=True)
    schedule_at = models.DateTimeField(null=True)
    started_at = models.DateTimeField(null=True)
    finish_at = models.DateTimeField(null=True)
    article = models.ForeignKey(DistArticle, null=True)


class SnsTaskDevice(models.Model):
    """
    任务具体设备
    """
    task = models.ForeignKey(SnsTask)
    device = models.ForeignKey(PhoneDevice)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)
    data = models.TextField(blank=True, null=True)
    schedule_at = models.DateTimeField(null=True)
    progress = models.IntegerField(default=0)


class DeviceFile(models.Model):
    """
    设备上传的文件信息
    """
    device = models.ForeignKey(PhoneDevice)
    qiniu_key = models.CharField(max_length=255)
    file_name = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(SnsTask)
    type = models.CharField(max_length=20)
    device_task = models.ForeignKey(SnsTaskDevice, null=True)


class SnsApplyTaskLog(models.Model):
    """
    加群的历史记录
    """
    device_task = models.ForeignKey(SnsTaskDevice, null=True)
    device = models.ForeignKey(PhoneDevice)
    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(SnsUser)
    group = models.ForeignKey(SnsGroup)
    memo = models.CharField(max_length=30)
    status = models.IntegerField(default=0)


class MenuItem(models.Model):
    menu_route = models.CharField(max_length=80)
    menu_name = models.CharField(max_length=20)
    menu_category = models.CharField(max_length=20)
    menu_icon = models.CharField(max_length=32)
    show_order = models.IntegerField(default=0)
    status = models.IntegerField(default=0)


class MenuItemPerm(models.Model):
    menu = models.ForeignKey(MenuItem)
    role = models.IntegerField(default=0)


class UserDelegate(models.Model):
    """
    授权给其他用户使用我的设备
    """
    owner = models.ForeignKey(User, related_name='owner')
    delegate = models.ForeignKey(User, related_name='delegate')

    class Meta:
        unique_together = ('owner', 'delegate')


class Tag(models.Model):
    """
    提炼的标签列表
    """
    name = models.CharField(max_length=10, primary_key=True)


class GroupTag(models.Model):
    group = models.ForeignKey(SnsGroup)
    tag = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'tag')


class TaskGroup(models.Model):
    """
    此次分发设计到的群，避免发多次
    """
    task = models.ForeignKey(SnsTask)
    group = models.ForeignKey(SnsGroup)
    sns_user = models.ForeignKey(SnsUser)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'group')


class DistTaskLog(models.Model):
    """
    分发群日志
    """
    task = models.ForeignKey(SnsTaskDevice)
    group = models.ForeignKey(SnsGroup)
    sns_user = models.ForeignKey(SnsUser)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10)
    success = models.IntegerField()


# 用户


class UserActionLog(models.Model):
    """
    用户操作历史
    """
    user = models.ForeignKey(User)
    action = models.CharField(max_length=20)

    memo = models.CharField(max_length=255)
    action_time = models.DateTimeField(auto_now_add=True)


class TaskWorkingLog(models.Model):
    """
    任务工作历史
    """
    device_task = models.ForeignKey(SnsTaskDevice)
    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(SnsUser)
    progress = models.IntegerField(default=0)

    class Meta:
        unique_together = ('device_task', 'account')


class UserDailyStat(models.Model):
    """
    用户马甲列表
    """
    report_date = models.CharField(max_length=20)
    app = models.ForeignKey(App)
    user = models.ForeignKey(User)
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_install = models.IntegerField()
    wx_install = models.IntegerField()


class AppDailyStat(models.Model):
    """
    生活圈统计
    """
    report_date = models.CharField(max_length=20)
    app = models.ForeignKey(App)
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_install = models.IntegerField()
    wx_install = models.IntegerField()


class DeviceTaskData(models.Model):
    device_task = models.ForeignKey(SnsTaskDevice)
    created_at = models.DateTimeField(auto_now_add=True)
    lines = models.TextField()


class SnsUserKickLog(models.Model):
    """
    qq号从QQ中被踢掉的记录
    """
    device_task = models.ForeignKey(SnsTaskDevice)
    sns_user = models.ForeignKey(SnsUser)
    created_at = models.DateTimeField(auto_now_add=True)


class DailyActive(models.Model):
    app = models.ForeignKey(App)
    iphone = models.IntegerField()
    android = models.IntegerField()
    total = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class DistArticleStatDetail(models.Model):
    article = models.ForeignKey(DistArticle)
    hour = models.IntegerField()
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_user = models.IntegerField()
    wx_user = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class DistArticleStat(models.Model):
    article = models.ForeignKey(DistArticle)
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_user = models.IntegerField()
    wx_user = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
