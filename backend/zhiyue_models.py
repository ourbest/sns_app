from django.db import models


class ZhiyueUser(models.Model):
    appId = models.CharField(max_length=30)
    name = models.CharField(max_length=50)
    userId = models.IntegerField(primary_key=True)

    class Meta:
        db_table = 'pojo_ZhiyueUser'
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

ITEM_TYPES = {
    'article-mochuang': '文章页魔窗',
    'article-down': '文章页连接下载',
    'tongji-down': '文章页长按二维码',
    'article-reshare': '微信文章二次分享',
    'qqarticle-reshare': 'QQ文章二次分享',
}