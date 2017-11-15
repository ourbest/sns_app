from django.db import models


class ZhiyueUser(models.Model):
    appId = models.CharField(max_length=30)
    name = models.CharField(max_length=50)
    userId = models.IntegerField(primary_key=True)

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'pojo_ZhiyueUser'
        managed = False


class ItemMore(models.Model):
    itemId = models.BigIntegerField(primary_key=True)
    appId = models.IntegerField()
    title = models.CharField(80)
    content = models.CharField(255)
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

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'clip_ClipItem'
        managed = False


class PartnerClipArticle(models.Model):
    articleId = models.IntegerField(primary_key=True)
    partnerId = models.IntegerField()
    item = models.ForeignKey(ClipItem, db_column='itemId')

    class Meta:
        db_table = 'partner_PartnerClipArticle'
        managed = False


class ShareArticleLog(models.Model):
    partnerId = models.IntegerField()
    article = models.ForeignKey(PartnerClipArticle, db_column='articleId', null=True)
    user = models.ForeignKey(ZhiyueUser, db_column='userId')
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
    sourceItemId = models.IntegerField()
    sourceUserId = models.IntegerField()

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
    user = models.ForeignKey(ZhiyueUser, db_column='userId', primary_key=True)
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

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'push_PushMessage'
        managed = False


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

    @staticmethod
    def db_name():
        return 'zhiyue'

    class Meta:
        db_table = 'partner_ShopCouponStatSum'
        managed = False
