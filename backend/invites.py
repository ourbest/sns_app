from django.utils import timezone

from backend import model_manager, dates, user_factory, remains, zhiyue
from backend.loggs import logger
from backend.models import InviteUser
from backend.zhiyue_models import InviteRecord, DeviceUser, InviteRewardRecord


def sync_user(from_date=None):
    date_range = (dates.today() if not from_date else from_date, timezone.now())
    saved = {x.user_id for x in InviteUser.objects.filter(created_at__range=date_range)}

    for record in model_manager.query(InviteRecord).filter(registerTime__range=date_range, status=1):
        if record.invitedUserId not in saved:
            dev_user = user_factory.get_reg_device(record.partnerId, record.invitedUserId)
            if dev_user:
                du = model_manager.query(DeviceUser).filter(deviceUserId=dev_user.userId).first()
                inv = user_factory.sync_to_invite_user(du)
                inv.user_id = record.invitedUserId
                logger.debug('sync invite user %s' % inv.user_id)
                inv.referer_id = record.userId
                inv.dev_user_id = dev_user.userId
                model_manager.save_ignore(inv)


def sync_remain():
    zhiyue.sync_obj_remain(InviteRecord)
    # remains.sync_remain_rt(InviteRecord)


def sync_award(from_date=None):
    date_range = (dates.today() if not from_date else from_date, timezone.now())
    for reward in model_manager.query(InviteRewardRecord).filter(get_time__range=date_range):
        # InviteUser.objects.filter(user_id=)
        pass
