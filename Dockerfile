FROM ourbest/python3

WORKDIR /code/
ADD requirements.txt .

RUN pip install -r requirements.txt

ADD . .

EXPOSE 8000

ENV TZ Asia/Shanghai

ENTRYPOINT ["sh", "entry.sh"]