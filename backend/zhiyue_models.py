import re
from django.db import models
from django.db.models import CASCADE


class ZhiyueUser(models.Model):
    appId = models.CharField(max_length=30)
    deviceId = models.CharField(max_length=64)
    name = models.CharField(max_length=50)
    userId = models.IntegerField(primary_key=True)
    platform = models.CharField(max_length=50)
    lastActiveTime = models.DateTimeField()
    screenName = models.CharField(max_length=50)
    createTime = models.DateTimeField()
    source = models.CharField(max_length=200)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'pojo_ZhiyueUser'
        managed = False


class ItemMore(models.Model):
    itemId = models.BigIntegerField(primary_key=True)
    appId = models.IntegerField()
    title = models.CharField(max_length=80)
    content = models.CharField(max_length=255)
    createTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_ItemMore'
        managed = False


class ClipItem(models.Model):
    clipId = models.IntegerField()
    itemId = models.IntegerField(primary_key=True)
    articleId = models.IntegerField()
    title = models.CharField(max_length=255)
    fromEntity = models.CharField(max_length=25)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'clip_ClipItem'
        managed = False


class PartnerClipArticle(models.Model):
    articleId = models.IntegerField(primary_key=True)
    partnerId = models.IntegerField()
    item = models.ForeignKey(ClipItem, db_column='itemId', on_delete=CASCADE)

    class Meta:
        db_table = 'partner_PartnerClipArticle'
        managed = False


class ShareArticleLog(models.Model):
    partnerId = models.IntegerField()
    article = models.ForeignKey(PartnerClipArticle, db_column='articleId', null=True, on_delete=CASCADE)
    user = models.ForeignKey(ZhiyueUser, db_column='userId', on_delete=CASCADE)
    deviceUserId = models.IntegerField()
    time = models.DateTimeField(primary_key=True)
    target = models.IntegerField()
    type = models.IntegerField()
    text = models.CharField(max_length=255)

    class Meta:
        db_table = 'datasystem_ShareArticleLog'
        managed = False


class WeizhanCount(models.Model):
    partnerId = models.IntegerField(primary_key=True)
    pcPV = models.IntegerField()
    mobilePV = models.IntegerField()
    downPage = models.IntegerField()
    appUser = models.IntegerField()
    time = models.DateTimeField()
    weizhanPv = models.IntegerField()

    @staticmethod
    def db_name():
        return 'partner'

    class Meta:
        db_table = 'datasystem_WeizhanCount'
        managed = False


class DeviceUser(models.Model):
    """
      `partnerId` bigint(20) DEFAULT NULL,
  `createTime` datetime DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `deviceUserId` bigint(20) NOT NULL DEFAULT '0',
  `deviceId` varchar(255) DEFAULT NULL,
  `ip` varchar(255) DEFAULT NULL,
  `deviceType` varchar(255) DEFAULT NULL,
  `extStr` varchar(255) DEFAULT NULL,
  `extStr2` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `updateTime` datetime DEFAULT NULL,
  `source` varchar(255) DEFAULT NULL COMMENT 'http://jira.cutt.com/confluence/pages/viewpage.action?pageId=30834742',
  `sourceItemId` bigint(20) DEFAULT NULL,
  `sourceUserId` bigint(20) DEFAULT NULL,
    """
    partnerId = models.IntegerField()
    createTime = models.DateTimeField()
    location = models.CharField(max_length=255)
    deviceUserId = models.IntegerField(primary_key=True)
    deviceId = models.CharField(max_length=255)
    ip = models.CharField(max_length=255)
    deviceType = models.CharField(max_length=255)
    extStr = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    source = models.CharField(max_length=255)
    sourceItemId = models.BigIntegerField()
    sourceUserId = models.BigIntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'datasystem_DeviceUser'
        managed = False


class HighValueUser(models.Model):
    name = models.CharField(max_length=255)
    userId = models.IntegerField(primary_key=True)
    deviceUserId = models.IntegerField()
    partnerId = models.IntegerField()
    shareNum = models.IntegerField()
    weizhanNum = models.IntegerField()
    downPageNum = models.IntegerField()
    appUserNum = models.IntegerField()
    commentNum = models.IntegerField()
    agreeNum = models.IntegerField()
    viewNum = models.IntegerField()
    secondShareNum = models.IntegerField()
    userType = models.IntegerField(help_text='userType=1 内容产生用户 ，userType=2 内容传播用户')
    time = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'partner'

    class Meta:
        db_table = 'datasystem_HighValueUser'
        managed = False


class AdminPartnerUser(models.Model):
    loginUser = models.CharField(max_length=255)
    user = models.ForeignKey(ZhiyueUser, db_column='userId', primary_key=True, on_delete=CASCADE)
    partnerId = models.IntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_AdminPartnerUser'
        managed = False


class PushMessage(models.Model):
    """
  `status` int(11) DEFAULT NULL COMMENT '-1:已取消;0:待推送;1:推送中;2:已推送;3:待审核;',
  `type` int(11) DEFAULT NULL,
  `appId` varchar(255) DEFAULT NULL,
  `message` varchar(255) DEFAULT NULL,
  `messageId` varchar(64) NOT NULL DEFAULT '',
  `createTime` datetime DEFAULT NULL,
  `articleId` bigint(20) DEFAULT NULL,
  `pushTime` datetime DEFAULT NULL,
  `scheduleTime` datetime DEFAULT NULL,
  `topicId` bigint(20) DEFAULT NULL,
  `clipId` bigint(20) DEFAULT NULL,
  `colId` bigint(20) DEFAULT '0',
  `cnt` int(11) DEFAULT '0',

    """
    messageId = models.CharField(max_length=64, primary_key=True)
    appId = models.CharField(max_length=255)
    message = models.CharField(max_length=255)
    status = models.IntegerField()
    createTime = models.DateTimeField()
    pushTime = models.DateTimeField()
    articleId = models.IntegerField()
    scheduleTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'push_PushMessage'
        managed = False

    @property
    def json(self):
        return {
            'message': self.message,
            'type': '全局',
            'articleId': self.articleId,
            'time': self.scheduleTime.strftime('%Y-%m-%d %H:%M')
        }


ITEM_TYPES = {
    'article-mochuang': '文章页魔窗',
    'article-down': '文章页连接下载',
    'tongji-down': '文章页长按二维码',
    'article-reshare': '微信文章二次分享',
    'qqarticle-reshare': 'QQ文章二次分享',
}


def get_article_title(item_id):
    item = ClipItem.objects.using('zhiyue').filter(itemId=item_id).first()
    if not item:
        return '（无此文章）'
    else:
        return item.title if item.title else '(无标题)'


class CouponInst(models.Model):
    partnerId = models.IntegerField()
    couponId = models.IntegerField()
    couponNum = models.IntegerField(primary_key=True)
    userId = models.BigIntegerField()
    useDate = models.DateTimeField()
    status = models.IntegerField()
    shopOwner = models.BigIntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_CouponInst'
        managed = False


class ShopCouponStatSum(models.Model):
    partnerId = models.IntegerField()
    ownerName = models.CharField(max_length=50)
    shopName = models.CharField(max_length=50)
    useDate = models.CharField(max_length=10)
    ownerId = models.IntegerField(primary_key=True)
    useNum = models.IntegerField()
    naNum = models.IntegerField()
    memo = models.CharField(max_length=20)
    remainDay = models.CharField(max_length=50)

    @property
    def json(self):
        remain = self.remainDay
        if remain:
            s = remain.split(';')[0]
            remain = int(s[2:]) if len(s) > 2 else 0
        else:
            remain = 0
        return {
            'name': '%s %s' % (self.ownerName, self.shopName),
            'app_id': self.partnerId,
            'date': self.useDate,
            'owner_id': self.ownerId,
            'total': self.useNum,
            'na': self.naNum,
            'remain': remain,
            'memo': self.memo,
            'ratio': '%s%%' % round(remain / self.useNum * 100)
        }

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_ShopCouponStatSum'
        managed = False


class UserRemain(models.Model):
    bizType = models.IntegerField()
    dateType = models.IntegerField()
    clipId = models.IntegerField()
    day = models.CharField(max_length=10, primary_key=True)
    value = models.CharField(max_length=20)
    platform = models.CharField(max_length=10)
    partnerId = models.IntegerField()

    @staticmethod
    def db_name():
        return 'cms'

    class Meta:
        db_table = 'report_UserRemain'


class UserRewardHistory(models.Model):
    partnerId = models.IntegerField()
    userId = models.IntegerField(primary_key=True)
    createTime = models.DateTimeField()
    source = models.CharField(max_length=20)
    type = models.IntegerField()
    amount = models.IntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_UserRewardHistory'
        managed = False


class WithdrawApply(models.Model):
    partnerId = models.IntegerField()
    userId = models.IntegerField(primary_key=True)
    amount = models.CharField(max_length=50)
    finishTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'shop_WithdrawApply'
        managed = False


class CouponDailyStatInfo(models.Model):
    partnerId = models.IntegerField()
    statDate = models.DateField(auto_now_add=True)
    total = models.IntegerField()
    active = models.IntegerField()
    open = models.IntegerField()
    remainDay = models.IntegerField()
    remainOpen = models.IntegerField()
    remainNotOpen = models.IntegerField()

    @staticmethod
    def db_name():
        return 'partner'

    class Meta:
        db_table = 'partner_CouponStatInfo'
        managed = False


class CouponPmSentInfo(models.Model):
    messageId = models.CharField(max_length=32, primary_key=True)
    userId = models.IntegerField()
    partnerId = models.IntegerField()
    createTime = models.DateTimeField()
    message = models.CharField(max_length=80)
    status = models.IntegerField()
    type = models.IntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_CouponPmSentInfo'
        managed = False


class AppConstants(models.Model):
    type = models.IntegerField()
    constType = models.CharField(max_length=64)
    constId = models.CharField(max_length=64, primary_key=True)
    constName = models.CharField(max_length=255)
    memo = models.CharField(max_length=255, null=True)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_AppConstants'
        managed = False


class OfflineDailyStat(models.Model):
    app_id = models.IntegerField()
    stat_date = models.CharField(max_length=12)
    user_num = models.IntegerField('新增', default=0)
    user_cost = models.IntegerField('花费', default=0)
    remain = models.IntegerField('留存', default=0)
    user_bonus_num = models.IntegerField('领取红包数', default=0)
    user_bonus_got = models.IntegerField('获得红包数', default=0)
    bonus_cost = models.IntegerField('红包奖励', default=0)
    bonus_cash = models.IntegerField('红包提取', default=0)
    user_cash_num = models.IntegerField('红包提取个数', default=0)
    total_cost = models.IntegerField('总花费', default=0)


class WeizhanItemView(models.Model):
    viewId = models.BigIntegerField(primary_key=True)
    itemType = models.CharField(max_length=20)
    ua = models.CharField(max_length=255)
    itemId = models.BigIntegerField()
    shareUserId = models.BigIntegerField()
    partnerId = models.IntegerField()
    time = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'datasystem_WeizhanItemView'
        managed = False


class CouponLog(models.Model):
    appId = models.IntegerField()
    couponId = models.IntegerField()
    num = models.CharField(max_length=10)
    actionTime = models.DateTimeField(primary_key=True)
    userId = models.BigIntegerField()
    action = models.IntegerField()
    lbs = models.CharField(max_length=50)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_CouponLog'
        managed = False


class UserRewardGroundHistory(models.Model):
    userId = models.BigIntegerField()
    type = models.IntegerField()
    createTime = models.DateTimeField(primary_key=True)
    partnerId = models.IntegerField()
    amount = models.IntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_UserRewardGroundHistory'
        managed = False


class ShareEventStat(models.Model):
    partnerId = models.BigIntegerField()
    userId = models.BigIntegerField(primary_key=True)
    statDate = models.CharField(max_length=20)
    amount = models.IntegerField()

    @staticmethod
    def db_name():
        return 'cms'

    class Meta:
        db_table = 'partner_ShareEventStat'
        managed = False


class ShareRewardEvent(models.Model):
    partnerId = models.BigIntegerField()
    userId = models.BigIntegerField(primary_key=True)
    createTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'cms'

    class Meta:
        db_table = 'partner_ShareRewardEvent'
        managed = False


class PushAuditLog(models.Model):
    messageId = models.CharField(max_length=64, primary_key=True)
    actionTime = models.DateTimeField()
    operator = models.CharField(max_length=64)
    reason = models.CharField(max_length=64)
    status = models.IntegerField()
    itemId = models.BigIntegerField()
    pushMessage = models.CharField(max_length=255)
    partnerId = models.BigIntegerField()

    @staticmethod
    def db_name():
        return 'cms'

    class Meta:
        db_table = 'cms_PushAuditLog'
        managed = False


class InviteRecord(models.Model):
    userId = models.BigIntegerField()
    phone = models.CharField(max_length=20)
    invitedUserId = models.BigIntegerField(null=True)
    registerTime = models.DateTimeField(null=True)
    status = models.IntegerField(default=0)
    partnerId = models.IntegerField()
    createTime = models.DateTimeField(primary_key=True)

    @staticmethod
    def db_name():
        return 'partner'

    class Meta:
        db_table = 'user_InviteRecord'
        managed = False


class InviteRewardRecord(models.Model):
    partnerId = models.IntegerField()
    userId = models.BigIntegerField()
    invitedUserId = models.BigIntegerField()
    taskId = models.IntegerField()
    rewardType = models.IntegerField()
    getTime = models.DateTimeField()
    createTime = models.DateTimeField()
    recordId = models.BigIntegerField(primary_key=True)

    @staticmethod
    def db_name():
        return 'partner'

    class Meta:
        db_table = 'user_InviteRewardRecord'
        managed = False


class UserDeviceHistory(models.Model):
    """
   CREATE TABLE `partner_UserDeviceHistory` (
  `appId` bigint(20) NOT NULL DEFAULT '0',
  `userId` bigint(20) NOT NULL DEFAULT '0',
  `loginTime` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `deviceId` varchar(64) NOT NULL DEFAULT '',
  `status` int(11) DEFAULT NULL,
  PRIMARY KEY (`appId`,`userId`,`loginTime`,`deviceId`),
  KEY `deviceId` (`deviceId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
    """
    appId = models.IntegerField()
    userId = models.BigIntegerField(primary_key=True)
    loginTime = models.DateTimeField()
    deviceId = models.CharField(max_length=64)
    status = models.IntegerField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_UserDeviceHistory'
        managed = False


class CustomPush(models.Model):
    pushId = models.IntegerField(primary_key=True)
    partnerId = models.IntegerField()
    pushDetail = models.CharField(max_length=255)
    pushType = models.CharField(max_length=20)
    itemId = models.BigIntegerField()
    status = models.IntegerField()
    createTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'policy_CustomPush'
        managed = False

    @property
    def json(self):
        return {
            'message': self.pushDetail,
            'articleId': self.itemId,
            'type': '个推',
            'time': self.createTime.strftime('%Y-%m-%d %H:%M')
        }

    @property
    def has_item(self):
        if self.itemId == 0:
            r = re.search(r'<a href="/article/(\d+)/0">(.+)</a>', self.pushDetail)
            if r:
                self.itemId = int(r.group(1))
                self.pushDetail = r.group(2)

        return self.itemId != 0


class MpSentItem(models.Model):
    userId = models.BigIntegerField()
    itemId = models.BigIntegerField()
    partnerId = models.IntegerField()
    sentTime = models.DateTimeField(primary_key=True)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_MpItemSent'
        managed = False


class ImageUploader(models.Model):
    imageId = models.CharField(max_length=50, default='', primary_key=True)
    userId = models.BigIntegerField()
    partnerId = models.BigIntegerField()
    createTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'cms'

    class Meta:
        db_table = 'cms_ImageUploader'
        managed = False


class PartnerImage(models.Model):
    imageId = models.CharField(max_length=64, primary_key=True)
    partnerId = models.BigIntegerField()
    createTime = models.DateTimeField()

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_PartnerImage'
        managed = False
