from backend.models import ChannelUser, ItemDeviceUser


def sync_to_channel_user(user, device_user):
    return ChannelUser(app_id=int(user.appId), ip=device_user.ip, city=device_user.city, location=device_user.location,
                       created_at=user.createTime)


def sync_to_item_dev_user(app, owner, device_user, majia):
    return ItemDeviceUser(app=app, owner=owner,
                          created_at=device_user.createTime,
                          user_id=device_user.deviceUserId,
                          item_id=device_user.sourceItemId,
                          type=majia.type,
                          ip=device_user.ip,
                          city=device_user.city,
                          cutt_user_id=majia.cutt_user_id,
                          location=device_user.location)