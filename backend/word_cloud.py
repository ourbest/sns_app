import jieba
import numpy as np
from PIL import Image
from wordcloud import WordCloud

from backend import model_manager
from backend.zhiyue_models import PushMessage


def push_cloud(app_id, img='tengzhou'):
    image = Image.open('data/%s_map.jpg' % img)
    image.convert('1')
    tz_map = np.array(image)
    titles = [' '.join(jieba.cut(x.message)) for x in
              model_manager.query(PushMessage).filter(appId=app_id, status=2).order_by('-pushTime')[:5000]]
    font = 'data/Songti.ttc'

    wc = WordCloud(background_color="white", font_path=font, max_words=1000, mask=tz_map)
    wc.generate(' '.join(titles))
    wc.to_file('data/%s.png' % img)
