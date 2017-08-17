from dj.utils import api_func_anonymous


@api_func_anonymous
def upload(ftype, fid):
    uploaded_file = None
    print(ftype, fid)


@api_func_anonymous
def image():
    pass


@api_func_anonymous
def qq_qr():
    pass


@api_func_anonymous
def import_qq():
    pass


@api_func_anonymous
def split_qq():
    pass


@api_func_anonymous
def send_qq():
    pass


def _after_upload_file(ftype, fid, local_file):
    pass
