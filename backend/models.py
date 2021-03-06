from django.db import models
from django.db.models import CASCADE


class App(models.Model):
    """
    生活圈
    """
    app_id = models.IntegerField('ID', primary_key=True)
    app_name = models.CharField('名称', max_length=32)
    stage = models.CharField('所处时期', max_length=20, default='准备期')
    self_qun = models.IntegerField('自行导入群', default=1, help_text="0 - 查群的结果平均分配给所有人，1 - 查群的结果分配给自己")
    price = models.FloatField('推广单价', default=0)
    cost = models.IntegerField('推广消耗', default=0)
    offline = models.IntegerField('是否在地推', default=0)
    center = models.CharField('城市中心坐标', max_length=100, null=True)

    @property
    def json(self):
        return {'id': self.app_id, 'name': self.app_name, 'center': self.center, 'stage': self.stage}

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
    status = models.IntegerField('状态', default=0, help_text="0 - 正常分发的操作者， 1 - 不分发的系统用户")
    passwd = models.CharField('密码', max_length=50)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    role = models.IntegerField(default=0, help_text='0-组员 1-组长')
    app = models.ForeignKey(App, verbose_name='生活圈', null=True, blank=True, default=None, on_delete=CASCADE)
    phone = models.CharField(max_length=20, help_text='手机号', null=True, blank=True)
    notify = models.IntegerField(default=0, null=True, help_text="是否接受钉钉通知")

    @property
    def json(self):
        x = self
        return {'id': x.id, 'email': x.email, 'name': x.name, 'role': x.role}

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '员工'
        verbose_name_plural = ' 员工列表'


class UserAuthApp(models.Model):
    """
    用户授权的APP列表
    """
    user = models.ForeignKey(User, on_delete=CASCADE)
    app = models.ForeignKey(App, on_delete=CASCADE)


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
    owner = models.ForeignKey(User, null=True, blank=True, verbose_name='所有者', on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    memo = models.CharField('备注', null=True, blank=True, max_length=50)
    in_trusteeship = models.BooleanField('托管', default=False)
    app = models.ForeignKey(App, null=True, blank=True, verbose_name='所属APP', on_delete=CASCADE)

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
    app = models.ForeignKey(App, null=True, on_delete=models.SET_NULL)
    memo = models.CharField('备注', max_length=50)
    created_at = models.DateTimeField('添加时间', auto_now_add=True)
    user = models.ForeignKey(User, verbose_name='属于', on_delete=CASCADE)

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
    status = models.IntegerField('状态', default=0, help_text='0 - 正常 -1 弃用的')
    memo = models.CharField('备注', max_length=255, null=True, blank=True)
    phone = models.CharField('绑定的电话号码', max_length=30)
    device = models.ForeignKey(PhoneDevice, null=True, verbose_name='登录的设备', on_delete=CASCADE)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    owner = models.ForeignKey(User, null=True, verbose_name='所有者', on_delete=CASCADE)
    app = models.ForeignKey(App, verbose_name='生活圈', on_delete=CASCADE)
    bot_login_token = models.BinaryField('字段未使用', null=True, blank=True)
    dist = models.IntegerField('用于分发', default=1)
    friend = models.IntegerField('可加群', default=1)
    search = models.IntegerField('可查群', default=0)
    provider = models.CharField('登录的软件(qq、tim)', default='qq', max_length=10)

    def __str__(self):
        return "%s(%s)" % (self.name, self.login_name)

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
    status = models.IntegerField('状态', default=0, help_text='0 - 未使用 1 - 已分配 -1 - 忽略 2 - 已加入')
    app = models.ForeignKey(App, verbose_name='生活圈', null=True, on_delete=CASCADE)
    created_at = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)
    quiz = models.CharField(verbose_name='问题答案', max_length=50, null=True, blank=True)
    from_user = models.ForeignKey(User, verbose_name='爬群用户', null=True, blank=True, on_delete=CASCADE)
    kick_times = models.IntegerField(default=0, verbose_name='被踢的次数')
    apply_count = models.IntegerField(default=0, verbose_name='申请次数')

    def __str__(self):
        return '%s (%s)' % (self.group_name, self.group_id)

    class Meta:
        verbose_name = '群'
        verbose_name_plural = '群列表'


class SnsUserGroup(models.Model):
    """
    QQ号加入的群
    """
    sns_user = models.ForeignKey(SnsUser, verbose_name='用户', on_delete=CASCADE)
    sns_group = models.ForeignKey(SnsGroup, verbose_name='群', on_delete=CASCADE)
    nick_name = models.CharField(max_length=50, verbose_name='备注名', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    status = models.IntegerField(default=0, verbose_name='状态', help_text='-1 - 被踢')
    active = models.IntegerField(default=0, verbose_name='可用')
    last_post_at = models.DateTimeField(null=True, verbose_name='最后分发时间')
    kick_times = models.IntegerField(default=0, verbose_name='被踢的次数')

    def __str__(self):
        return "%s @ %s" % (self.sns_user, self.sns_group)

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
    group = models.ForeignKey(SnsGroup, verbose_name='群', on_delete=CASCADE)
    user = models.ForeignKey(SnsUserInfo, verbose_name='用户', on_delete=CASCADE)
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
    group = models.ForeignKey(SnsGroup, verbose_name='群', on_delete=CASCADE)
    user = models.ForeignKey(User, verbose_name='推广人', on_delete=CASCADE)
    status = models.IntegerField('状态', default=0, help_text='0 默认 1 已发送 2 已申请 3 已通过 -1 忽略')
    created_at = models.DateTimeField('添加时间', auto_now_add=True)
    updated_at = models.DateTimeField('修改时间', auto_now=True, null=True)
    phone = models.ForeignKey(PhoneDevice, null=True, verbose_name='设备', on_delete=CASCADE)
    apply_count = models.IntegerField(default=0)
    app = models.ForeignKey(App, verbose_name='所属APP', null=True, blank=True, on_delete=CASCADE)

    def __str__(self):
        return '<Splitter:%s@%s_%s>' % (self.group_id, self.phone_id, self.user_id)


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
    group = models.ForeignKey(SnsGroup, verbose_name='群', on_delete=CASCADE)
    sns_user = models.ForeignKey(SnsUser, verbose_name='账号', on_delete=CASCADE)
    status = models.IntegerField('状态', default=0, help_text='0 - 未处理, 1 - 已处理')
    created_at = models.DateTimeField('添加时间', auto_now_add=True)


class SnsTaskType(models.Model):
    """
    任务类型，字典表，记录1,2，3,4,5
    """
    name = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    memo = models.CharField(max_length=255, null=True)


class ActiveDevice(models.Model):
    """
    当前在线的设备
    """
    device = models.ForeignKey(PhoneDevice, verbose_name='设备', on_delete=CASCADE)
    active_at = models.DateTimeField('最后上线时间', auto_now=True)
    status = models.IntegerField('状态', default=0, help_text='0 - 正常， 1 - 工作中')


class DistArticle(models.Model):
    """
    分发的文章
    """
    item_id = models.IntegerField('cutt内部文章ID', unique=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    title = models.CharField('文章标题', max_length=255)
    delete_flag = models.IntegerField('是否已删除', default=0)
    category = models.CharField('文章类型', max_length=30, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField('第一次分发时间', null=True, blank=True)
    last_started_at = models.DateTimeField('最后一次分发时间', null=True, blank=True)


class SnsTask(models.Model):
    """
    任务
    """
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.ForeignKey(SnsTaskType, on_delete=CASCADE)
    data = models.TextField('参数', blank=True, null=True)
    status = models.IntegerField('状态', default=0, help_text='0 - 初始  1 - 进行中  2 - 已完成')
    app = models.ForeignKey(App, null=True, on_delete=CASCADE)
    creator = models.ForeignKey(User, null=True, on_delete=CASCADE)
    schedule_at = models.DateTimeField('定时发送的时间', null=True)
    started_at = models.DateTimeField('启动时间', null=True)
    finish_at = models.DateTimeField('结束时间', null=True)
    article = models.ForeignKey(DistArticle, null=True, on_delete=CASCADE, verbose_name='对应的文章')

    def __str__(self):
        return '<SnsTask %s>' % self.pk


class SnsTaskDevice(models.Model):
    """
    任务具体设备
    """
    task = models.ForeignKey(SnsTask, on_delete=CASCADE)
    device = models.ForeignKey(PhoneDevice, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0, help_text='0 - 初始  1 - 进行中  2 - 已完成 取消 暂停')
    started_at = models.DateTimeField(null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)
    data = models.TextField('参数', blank=True, null=True)
    schedule_at = models.DateTimeField(null=True)
    progress = models.IntegerField('进度', default=0)
    pv = models.IntegerField('pv', default=0, null=True)

    def __str__(self):
        return '%s@%s' % (self.task if self.task else 'N/A', self.device if self.device else 'N/A')


class DeviceFile(models.Model):
    """
    设备上传的文件信息
    """
    device = models.ForeignKey(PhoneDevice, on_delete=CASCADE, verbose_name='手机')
    qiniu_key = models.CharField('保存到文件服务器的名字', max_length=255)
    file_name = models.CharField('文件名', max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(SnsTask, on_delete=CASCADE)
    type = models.CharField('类型', max_length=20, help_text='日志log, 截图image')
    device_task = models.ForeignKey(SnsTaskDevice, null=True, on_delete=CASCADE)


class SnsApplyTaskLog(models.Model):
    """
    加群的历史记录
    """
    device_task = models.ForeignKey(SnsTaskDevice, null=True, on_delete=CASCADE)
    device = models.ForeignKey(PhoneDevice, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(SnsUser, on_delete=CASCADE)
    group = models.ForeignKey(SnsGroup, on_delete=CASCADE)
    memo = models.CharField('结果文字', max_length=30)
    status = models.IntegerField(default=0)


class MenuItem(models.Model):
    """
    推广后台的菜单项
    """
    menu_route = models.CharField('菜单的英文名', max_length=80)
    menu_name = models.CharField('菜单的名字', max_length=20)
    menu_category = models.CharField('类型（目录、功能）', max_length=20)
    menu_icon = models.CharField('图标', max_length=32)
    show_order = models.IntegerField('显示顺序', default=0)
    status = models.IntegerField(default=0)


class MenuItemPerm(models.Model):
    """
    菜单角色对应表
    """
    menu = models.ForeignKey(MenuItem, on_delete=CASCADE)
    role = models.IntegerField('角色', default=0, help_text='0 - 所有人 1 - 组长 2 - 管理')


class UserDelegate(models.Model):
    """
    授权给其他用户使用我的设备
    """
    owner = models.ForeignKey(User, related_name='owner', on_delete=CASCADE)
    delegate = models.ForeignKey(User, related_name='delegate', on_delete=CASCADE)

    class Meta:
        unique_together = ('owner', 'delegate')


class Tag(models.Model):
    """
    提炼的标签列表 (QQ群的标签)
    """
    name = models.CharField(max_length=10, primary_key=True)


class GroupTag(models.Model):
    group = models.ForeignKey(SnsGroup, on_delete=CASCADE)
    tag = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'tag')


class TaskGroup(models.Model):
    """
    一次分发设计到的群，避免发多次，在给机器人发送数据之前生成
    """
    task = models.ForeignKey(SnsTask, on_delete=CASCADE)
    group = models.ForeignKey(SnsGroup, on_delete=CASCADE)
    sns_user = models.ForeignKey(SnsUser, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'group')


class DistTaskLog(models.Model):
    """
    分发群日志
    """
    task = models.ForeignKey(SnsTaskDevice, on_delete=CASCADE)
    group = models.ForeignKey(SnsGroup, on_delete=CASCADE)
    sns_user = models.ForeignKey(SnsUser, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10)
    success = models.IntegerField('1 成功或 0 失败')


class WxDistLog(models.Model):
    """
    微信分发日志
    """
    task = models.ForeignKey(SnsTaskDevice, on_delete=CASCADE)
    group_name = models.CharField(max_length=100)
    user_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    dist = models.IntegerField(default=0, null=True)


# 用户
class UserActionLog(models.Model):
    """
    用户操作历史
    """
    user = models.ForeignKey(User, on_delete=CASCADE)
    action = models.CharField(max_length=20)

    memo = models.CharField(max_length=255)
    action_time = models.DateTimeField(auto_now_add=True)


class TaskWorkingLog(models.Model):
    """
    任务工作历史
    """
    device_task = models.ForeignKey(SnsTaskDevice, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(SnsUser, on_delete=CASCADE)
    progress = models.IntegerField(default=0)

    class Meta:
        unique_together = ('device_task', 'account')


class UserDailyStat(models.Model):
    """
    用户日统计
    """
    report_date = models.CharField('统计日期', max_length=20)
    app = models.ForeignKey(App, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=CASCADE)
    qq_pv = models.IntegerField('QQ PV')
    wx_pv = models.IntegerField('微信 PV')
    qq_down = models.IntegerField('QQ 下载页打开次数')
    wx_down = models.IntegerField('微信下载页打开次数')
    qq_install = models.IntegerField('QQ安装数')
    wx_install = models.IntegerField('微信安装数')
    qq_remain = models.IntegerField('次日留存', default=0)
    wx_remain = models.IntegerField('次日留存', default=0)


class UserDailyDeviceUser(models.Model):
    """
    关联安装用户的列表
    """
    report_date = models.CharField('统计日期', max_length=20)
    app = models.ForeignKey(App, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=CASCADE)
    qq_user_ids = models.TextField()
    wx_user_ids = models.TextField()


class ItemDeviceUser(models.Model):
    """
    关联安装情况
    """
    app = models.ForeignKey(App, on_delete=CASCADE)
    owner = models.ForeignKey(User, on_delete=CASCADE)
    created_at = models.DateTimeField()
    user_id = models.BigIntegerField(unique=True)
    item_id = models.BigIntegerField(default=0)
    type = models.IntegerField(default=0, help_text='0 - QQ, 1 - 微信')
    remain = models.IntegerField(default=0)
    ip = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=50, default='')
    location = models.CharField(max_length=100, default='', null=True)
    cutt_user_id = models.BigIntegerField(default=0, null=True)
    remain_7 = models.IntegerField(default=0)
    remain_14 = models.IntegerField(default=0)
    platform = models.CharField(max_length=20, default='android', null=True)
    region = models.CharField(max_length=30, null=True)
    view = models.IntegerField(default=0, null=True)

    @property
    def json(self):
        return {
            'owner_id': self.owner_id,
            'type': self.type,
            'owner': '%s_%s' % (self.owner_id, self.type),
            'location': self.location,
            'city': self.city,
            'remain': self.remain,
            'platform': self.platform,
        }

    def __str__(self):
        return "(User-%s)" % self.user_id


class AppDailyStat(models.Model):
    """
    生活圈统计
    """
    report_date = models.CharField(max_length=20)
    app = models.ForeignKey(App, on_delete=CASCADE)
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_install = models.IntegerField()
    wx_install = models.IntegerField()
    qq_remain = models.IntegerField('次日留存数', default=0)
    wx_remain = models.IntegerField('次日留存数', default=0)

    @property
    def json(self):
        return {
            'app_name': self.app.app_name[:-3],
            'app_id': self.app_id,
            'pv': self.qq_pv + self.wx_pv,
            'users': self.qq_install + self.wx_install,
            'remain': self.qq_remain + self.wx_remain,
            'report_date': self.report_date,
        }


class DeviceTaskData(models.Model):
    """
    TG后台给机器人发送的所有任务参数数据
    """
    device_task = models.ForeignKey(SnsTaskDevice, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    lines = models.TextField()


class SnsUserKickLog(models.Model):
    """
    qq号从QQ中被踢掉的记录
    """
    device_task = models.ForeignKey(SnsTaskDevice, on_delete=CASCADE)
    sns_user = models.ForeignKey(SnsUser, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class DailyActive(models.Model):
    """
    生活圈日活数据
    """
    app = models.ForeignKey(App, on_delete=CASCADE)
    iphone = models.IntegerField()
    android = models.IntegerField()
    total = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class DistArticleStatDetail(models.Model):
    """
    分发的文章对应的统计数据
    """
    article = models.ForeignKey(DistArticle, on_delete=CASCADE)
    hour = models.IntegerField()
    qq_pv = models.IntegerField()
    wx_pv = models.IntegerField()
    qq_down = models.IntegerField()
    wx_down = models.IntegerField()
    qq_user = models.IntegerField('关联安装数')
    wx_user = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class DistArticleStat(models.Model):
    """
    分发的文章对应的统计数据
    """
    article = models.ForeignKey(DistArticle, on_delete=CASCADE)
    qq_pv = models.IntegerField('PV', default=0)
    wx_pv = models.IntegerField(default=0)
    qq_down = models.IntegerField('下载页', default=0)
    wx_down = models.IntegerField(default=0)
    qq_user = models.IntegerField('关联安装', default=0)
    wx_user = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dist_qq_user_count = models.IntegerField('分发的QQ数', default=0)
    dist_wx_user_count = models.IntegerField('分发的微信数', default=0)
    dist_qq_phone_count = models.IntegerField('分发的QQ手机数', default=0)
    dist_wx_phone_count = models.IntegerField('分发的微信手机数', default=0)
    dist_qun_count = models.IntegerField('群数', default=0)
    dist_qun_user = models.IntegerField('群用户数', default=0)
    qq_remain = models.IntegerField(default=0)
    wx_remain = models.IntegerField(default=0)


class DeviceWeixinGroup(models.Model):
    """
    设备的微信群
    """
    device = models.ForeignKey(PhoneDevice, on_delete=CASCADE)
    name = models.CharField('群名', max_length=100)
    member_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_dist_at = models.DateTimeField(null=True, db_index=True)


class DeviceWeixinGroupLost(models.Model):
    """
    可能被踢的群（只是可能）
    """
    device = models.ForeignKey(PhoneDevice, on_delete=CASCADE)
    name = models.CharField('群名', max_length=100)
    member_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class UserDailyResourceStat(models.Model):
    """
    用户的日统计数据
    """
    app = models.ForeignKey(App, on_delete=CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=CASCADE)
    stat_date = models.DateField(auto_now_add=True)
    qq_cnt = models.IntegerField()
    wx_cnt = models.IntegerField(default=0)
    phone_cnt = models.IntegerField()
    qq_acc_cnt = models.IntegerField()
    qq_group_cnt = models.IntegerField()
    wx_group_cnt = models.IntegerField()
    qq_uniq_group_cnt = models.IntegerField()
    wx_uniq_group_cnt = models.IntegerField()
    qq_apply_cnt = models.IntegerField()
    qq_lost_cnt = models.IntegerField()
    wx_lost_cnt = models.IntegerField()
    qq_members = models.IntegerField(default=0)
    wx_members = models.IntegerField(default=0)


class AppDailyResourceStat(models.Model):
    """
    生活圈资源情况
    """
    app = models.ForeignKey(App, on_delete=CASCADE)
    stat_date = models.DateField(auto_now_add=True)
    qq_cnt = models.IntegerField('QQ分发数')
    wx_cnt = models.IntegerField('微信分发数')
    phone_cnt = models.IntegerField('手机个数')
    qq_acc_cnt = models.IntegerField('QQ账号数')
    qq_group_cnt = models.IntegerField('QQ群数')
    wx_group_cnt = models.IntegerField('微信群数')
    qq_uniq_group_cnt = models.IntegerField('排重后')
    wx_uniq_group_cnt = models.IntegerField()
    qq_apply_cnt = models.IntegerField('QQ申请数')
    qq_lost_cnt = models.IntegerField('QQ群被踢数')
    wx_lost_cnt = models.IntegerField()
    qq_group_new_cnt = models.IntegerField('新群')
    qq_group_total = models.IntegerField()
    qq_members = models.IntegerField(default=0)
    wx_members = models.IntegerField(default=0)


class AppWeeklyStat(models.Model):
    """
    线上推广周报
    """
    app = models.ForeignKey(App, on_delete=CASCADE)
    stat_date = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    qq_pv = models.IntegerField()
    qq_down = models.IntegerField(default=0)
    qq_user = models.IntegerField(default=0)
    wx_pv = models.IntegerField()
    wx_down = models.IntegerField(default=0)
    wx_user = models.IntegerField()
    qq_remain = models.IntegerField(default=0)
    wx_remain = models.IntegerField(default=0)
    operators = models.IntegerField()
    phone_cnt = models.IntegerField(default=0)
    qq_acc_cnt = models.IntegerField()
    qq_cnt = models.IntegerField('qq分发数')
    wx_cnt = models.IntegerField('微信分发数')
    qq_group_cnt = models.IntegerField()
    wx_group_cnt = models.IntegerField()
    qq_uniq_group_cnt = models.IntegerField()
    wx_uniq_group_cnt = models.IntegerField()
    qq_apply_cnt = models.IntegerField()
    qq_lost_cnt = models.IntegerField()
    qq_group_new_cnt = models.IntegerField('新群')
    qq_group_total = models.IntegerField()
    qq_members = models.IntegerField(default=0)
    wx_members = models.IntegerField(default=0)


class ArticleDailyInfo(models.Model):
    """
    每日PV汇总
    """
    app = models.ForeignKey(App, on_delete=CASCADE)
    stat_date = models.CharField('统计日期', max_length=15)
    user = models.ForeignKey(User, on_delete=CASCADE, null=True)
    item_id = models.BigIntegerField("分发的文章")
    majia_id = models.BigIntegerField("分发马甲")
    majia_type = models.IntegerField(default=0)
    pv = models.IntegerField(default=0)
    uv = models.IntegerField(default=0)
    reshare = models.IntegerField(default=0)
    down = models.IntegerField('下载页', default=0)
    mobile_pv = models.IntegerField(default=0)
    query_time = models.DateTimeField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    android_pv = models.IntegerField(default=0)
    iphone_pv = models.IntegerField(default=0)
    android_down = models.IntegerField(default=0)
    iphone_down = models.IntegerField(default=0)


class RuntimeData(models.Model):
    name = models.CharField(max_length=20, primary_key=True)
    value = models.CharField(max_length=255)


class OfflineUser(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    created_at = models.DateTimeField()
    owner = models.BigIntegerField('扫描人', default=0)
    remain = models.IntegerField(default=0)
    location = models.CharField(max_length=100, default='', null=True)
    bonus_view = models.IntegerField(default=0)
    bonus_pick = models.IntegerField(default=0)
    bonus_step = models.IntegerField(default=0)
    bonus_amount = models.IntegerField(default=0)
    bonus_got = models.IntegerField(default=0)
    bonus_withdraw = models.IntegerField(default=0)
    bonus_time = models.DateTimeField(null=True)
    withdraw_time = models.DateTimeField(null=True)
    remain_7 = models.IntegerField(default=0)
    remain_14 = models.IntegerField(default=0)
    remain_30 = models.IntegerField(default=0)

    @property
    def json(self):
        return {
            'user_id': self.user_id,
            'remain': self.remain,
            'location': self.location,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'withdraw_time': self.withdraw_time.strftime('%Y-%m-%d %H:%M') if self.withdraw_time else None,
            'bonus_pick': self.bonus_pick,
            'bonus_view': self.bonus_view,
            'bonus_step': self.bonus_step,
            'bonus_amount': self.bonus_amount,
            'bonus_withdraw': self.bonus_withdraw,
            'bonus_got': self.bonus_got,
        }


class KPIPeriod(models.Model):
    app = models.ForeignKey(App, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    from_date = models.CharField(max_length=20)
    to_date = models.CharField(max_length=20)
    pv = models.IntegerField(default=0)
    users = models.IntegerField(default=0)
    remains = models.IntegerField(default=0)
    editors = models.CharField(max_length=255)
    status = models.IntegerField(default=0)

    def __str__(self):
        return "{} - {}".format(self.from_date, self.to_date)

    @property
    def json(self):
        editors = []
        if self.editors:
            editors = [x.name for x in User.objects.filter(pk__in=self.editors.split(','))]
        return {
            'id': self.id,
            'label': str(self),
            'from_date': self.from_date,
            'to_date': self.to_date,
            'pv': self.pv,
            'users': self.users,
            'remain': self.remains,
            'editors': '/'.join(editors),
        }


class ChannelUser(models.Model):
    """
    渠道用户
    """
    user_id = models.BigIntegerField(primary_key=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    channel = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    remain = models.IntegerField(default=0)
    ip = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=50, default='')
    location = models.CharField(max_length=100, default='', null=True)
    remain_7 = models.IntegerField(default=0)
    remain_14 = models.IntegerField(default=0)

    @property
    def json(self):
        return {
            'user_id': self.user_id,
            'remain': self.remain,
            'location': self.location,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'app_id': self.app_id,
            'channel': self.channel,
            'ip': self.ip,
            'city': self.city,
        }


class ShareUser(models.Model):
    """
    分享活动带来的新增
    """
    user_id = models.BigIntegerField(primary_key=True)
    app = models.ForeignKey(App, on_delete=CASCADE)
    referer_id = models.BigIntegerField('分享人', db_index=True)
    created_at = models.DateTimeField()
    remain = models.IntegerField(default=0)
    ip = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=50, default='')
    location = models.CharField(max_length=100, default='', null=True)
    remain_7 = models.IntegerField(default=0)
    remain_14 = models.IntegerField(default=0)
    enrolled = models.IntegerField(default=0)

    @property
    def json(self):
        return {
            'user_id': self.user_id,
            'remain': self.remain,
            'referer_id': self.referer_id,
            'location': self.location,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'app_id': self.app_id,
            'ip': self.ip,
            'city': self.city,
        }


class InviteUser(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    dev_user_id = models.BigIntegerField()
    app = models.ForeignKey(App, on_delete=CASCADE)
    referer_id = models.BigIntegerField('邀请人', db_index=True)
    user_award = models.IntegerField(default=0)
    refer_award = models.IntegerField(default=0)
    task_success = models.IntegerField(default=0)
    user_withdraw = models.IntegerField(default=0)
    refer_withdraw = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    remain = models.IntegerField(default=0)
    ip = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=50, default='')
    location = models.CharField(max_length=100, default='', null=True)
    remain_7 = models.IntegerField(default=0)
    remain_14 = models.IntegerField(default=0)

    @property
    def json(self):
        return {
            'user_id': self.user_id,
            'remain': self.remain,
            'referer_id': self.referer_id,
            'success': self.task_success,
            'location': self.location,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'app_id': self.app_id,
            'ip': self.ip,
            'city': self.city,
        }


class SecondaryTaskLog(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    device = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE)
    type = models.CharField(max_length=20)
    data = models.TextField(null=True, blank=True)


class ShortenURL(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    url = models.CharField(max_length=100)

    @property
    def json(self):
        return {
            'id': self.id,
            'url': self.url,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
        }


class UserAuth(models.Model):
    user = models.OneToOneField(to=User, on_delete=CASCADE)
    password = models.CharField(max_length=255)


class DailyDetailData(models.Model):
    app = models.ForeignKey(App, on_delete=CASCADE)
    item_id = models.BigIntegerField()
    sns_type = models.IntegerField()
    title = models.TextField(max_length=255)
    category = models.CharField(max_length=10)
    date = models.CharField(max_length=12)
    total_user = models.IntegerField()
    android_user = models.IntegerField()
    iphone_user = models.IntegerField()
    total_pv = models.IntegerField()
    android_pv = models.IntegerField()
    iphone_pv = models.IntegerField()
    total_down = models.IntegerField()
    iphone_down = models.IntegerField()
    android_down = models.IntegerField()
    total_remain = models.IntegerField()
    android_remain = models.IntegerField()
    iphone_remain = models.IntegerField()

    class Meta:
        unique_together = (('app', 'item_id', 'sns_type', 'date'),)


class CallingList(models.Model):
    calling = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE, verbose_name='主叫设备', related_name='calling')
    calling_qq = models.ForeignKey(SnsUser, on_delete=models.CASCADE, verbose_name='主叫QQ', related_name='calling')
    called = models.ForeignKey(PhoneDevice, on_delete=models.CASCADE, verbose_name='被叫设备', related_name='called')
    called_qq = models.ForeignKey(SnsUser, on_delete=models.CASCADE, verbose_name='被叫QQ', null=True, blank=True,
                                  related_name='called')
    status = models.IntegerField(default=0, help_text='''
                                            0-calling创建请求
                                            1-calling切换到指定QQ
                                            2-called查看了请求
                                            3-called返回在线qq号
                                            4-calling查看了qq号
                                            5-calling已呼叫
                                            6-called接到呼叫
                                            7-calling确认已接
                                            ''')
    change_time = models.DateTimeField(auto_now=True)
    success_or_failure = models.NullBooleanField()
    failure_reason = models.CharField(max_length=30, null=True, blank=True)


class WeizhanClick(models.Model):
    """
    微站PV
    """
    app_id = models.IntegerField(db_index=True)
    item_id = models.BigIntegerField(default=0)
    uid = models.BigIntegerField(default=0)
    ua = models.CharField(max_length=255)
    qq = models.CharField(max_length=20)
    ts2 = models.CharField(max_length=20)
    uuid = models.CharField(max_length=32)
    ts = models.DateTimeField(db_index=True)
    platform = models.CharField(max_length=10)
    net = models.CharField(max_length=10, default='WIFI')
    ip = models.CharField(max_length=20)
    from_param = models.CharField(max_length=20, default='')
    tid = models.IntegerField(null=True, default=0)
    is_installed = models.IntegerField(default=0)

    class Meta:
        unique_together = (('item_id', 'uuid', 'uid', 'tid'),)


class WeizhanDownClick(models.Model):
    """
    微站下载页点开的数据
    """
    app_id = models.IntegerField(db_index=True)
    item_id = models.BigIntegerField(default=0)
    type = models.CharField(max_length=30, default='')
    uid = models.BigIntegerField(default=0)
    img = models.CharField(max_length=255, default='')
    href = models.CharField(max_length=255, default='')
    idx = models.IntegerField(default=0)
    tid = models.IntegerField(default=0)
    net = models.CharField(max_length=10, default='WIFI')
    platform = models.CharField(max_length=20, default='android')
    ip = models.CharField(max_length=20)
    uuid = models.CharField(max_length=32)
    ts = models.DateTimeField(db_index=True)
    ua = models.CharField(max_length=255, default='')
    qq = models.CharField(max_length=10, default='', null=True)
    task_id = models.IntegerField(null=True, default=0)

    class Meta:
        unique_together = (('item_id', 'uuid', 'uid', 'task_id'),)


class WeizhanClickDaily(models.Model):
    app_id = models.IntegerField(db_index=True)
    stat_date = models.CharField(max_length=10)
    item_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    task_id = models.IntegerField(default=0)
    qq_id = models.IntegerField(default=0)
    platform = models.CharField(max_length=10)
    sns_type = models.IntegerField(default=0)
    cnt = models.IntegerField(default=0)
    down_page_cnt = models.IntegerField(default=0)


class WeizhanDlClickDaily(models.Model):
    app_id = models.IntegerField(db_index=True)
    stat_date = models.CharField(max_length=10)
    item_id = models.BigIntegerField()
    user_id = models.BigIntegerField()
    task_id = models.IntegerField(default=0)
    qq_id = models.IntegerField(default=0)
    platform = models.CharField(max_length=10)
    sns_type = models.IntegerField(default=0)
    type = models.CharField(max_length=20)
    cnt = models.IntegerField(default=0)


class UserFollowApp(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class DingTalkToken(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    token = models.CharField(max_length=64)
    memo = models.CharField(max_length=64)


class AuditImage(models.Model):
    image_id = models.CharField(max_length=64, primary_key=True)
    image_hash = models.CharField(max_length=64, db_index=True, default='')
    app_id = models.IntegerField()
    user_id = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=0)
    ua = models.CharField(default=None, null=True, blank=True, max_length=255)


class DeviceUserExtra(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    app_id = models.IntegerField()
    created_at = models.DateTimeField()
    ip = models.CharField(max_length=20, default='')
    city = models.CharField(max_length=50, default='')
    location = models.CharField(max_length=100, default='', null=True)
    region = models.CharField(max_length=100, default="")
    view_source_item = models.IntegerField(default=0, verbose_name='是否查看关联安装文章')
    remain = models.IntegerField(default=0)
    area = models.CharField(max_length=20)
    area_type = models.IntegerField(default=-1, help_text='0 - 主城区，1 - 县城，2 - 外地')
    platform = models.CharField(max_length=10, help_text='iphone/android')
    lbs_flag = models.IntegerField(default=-1, verbose_name='是否打开gps')
    view_items = models.IntegerField(verbose_name='第一次查看文章次数(30分钟内)', default=0)
    open_push = models.IntegerField(verbose_name='是否打开推送', default=0)
    view_push = models.IntegerField(verbose_name='是否查看推送', default=0)
    view_clips = models.IntegerField(verbose_name='查看的栏目个数', default=0)
    sign_on = models.IntegerField(verbose_name='是否登录', default=0)
    open_times = models.IntegerField(default=0, verbose_name='第一天打开APP次数')

    @staticmethod
    def db_name():
        return 'zhiyue_rw'
