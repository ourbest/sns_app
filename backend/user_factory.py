from backend.models import ChannelUser, ItemDeviceUser, ShareUser, InviteUser
from backend.zhiyue_models import UserDeviceHistory, ZhiyueUser


def sync_to_channel_user(user, device_user):
    return ChannelUser(app_id=int(user.appId), ip=device_user.ip, city=device_user.city,
                       channel=user.source, location=device_user.location,
                       created_at=user.createTime, user_id=device_user.deviceUserId)


def sync_to_item_dev_user(app, owner, device_user, majia):
    return ItemDeviceUser(app=app, owner=owner,
                          created_at=device_user.createTime,
                          user_id=device_user.deviceUserId,
                          item_id=device_user.sourceItemId,
                          type=majia.type,
                          ip=device_user.ip,
                          city=device_user.city,
                          cutt_user_id=majia.cutt_user_id,
                          location=device_user.location,
                          platform='iphone' if 'iPhone' in device_user.extStr else 'android')


def sync_to_share_dev_user(device_user):
    return ShareUser(app_id=device_user.partnerId,
                     created_at=device_user.createTime,
                     user_id=device_user.deviceUserId,
                     referer_id=device_user.sourceUserId,
                     ip=device_user.ip,
                     city=device_user.city,
                     location=device_user.location)


def sync_to_invite_user(device_user):
    return InviteUser(app_id=device_user.partnerId,
                      created_at=device_user.createTime,
                      user_id=device_user.deviceUserId,
                      referer_id=device_user.sourceUserId,
                      ip=device_user.ip,
                      city=device_user.city,
                      location=device_user.location)


def get_reg_device(app_id, user_id):
    from backend import model_manager
    device = model_manager.query(UserDeviceHistory).filter(appId=app_id, userId=user_id).order_by("loginTime").first()

    return model_manager.query(ZhiyueUser).filter(appId=app_id, deviceId=device.deviceId).first() if device else None
