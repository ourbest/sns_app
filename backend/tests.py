# Create your tests here.
from backend.models import SnsGroupSplit, SnsGroup


def clean_split_data():
    splits = SnsGroupSplit.objects.filter(status=0)
    done = set()
    for x in splits:
        if not done.add(x.group_id):
            x.delete()


def clean_split_data_1(status=1):
    splits = SnsGroupSplit.objects.filter(status=status)
    done = set()
    for x in splits:
        size = len(done)
        done.add(x.group_id)
        if len(done) == size:
            x.delete()


def sync_split():
    groups = SnsGroup.objects.filter(status=1, app_id=1519662)
    for group in groups:
        if group.snsgroupsplit_set.count() == 0 and group.snsusergroup_set.count() == 0:
            group.status = 0
            group.save()
