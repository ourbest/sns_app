FROM ourbest/python3

WORKDIR /code/
ADD requirements.txt .

RUN pip install -r requirements.txt

ADD . .

EXPOSE 8000

ENTRYPOINT ["sh", "entry.sh"]