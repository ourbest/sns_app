FROM ourbest/python3

WORKDIR /code/
ADD requirements.txt .

RUN pip install -r requirements.txt -i https://pypi.douban.com/simple

ENV TZ Asia/Shanghai
EXPOSE 8000
ADD . .
ENTRYPOINT ["sh", "entry.sh"]