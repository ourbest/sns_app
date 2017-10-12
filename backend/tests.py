# Create your tests here.
from backend.models import SnsGroupSplit


def clean_split_data():
    splits = SnsGroupSplit.objects.filter(status=0)
    done = set()
    for x in splits:
        if not done.add(x.group_id):
            x.delete()
