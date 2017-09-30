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
