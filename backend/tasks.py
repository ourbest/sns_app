from dj import times
from dj.utils import api_func_anonymous

from backend.models import TaskWorkingLog


@api_func_anonymous
def work_logs(i_id):
    return {
        'items': [{
            'start': times.to_str(x.created_at),
            'qq': x.account.login_name,
            'progress': x.progress
        } for x in TaskWorkingLog.objects.filter(device_task_id=i_id).order_by("-pk")]
    }
