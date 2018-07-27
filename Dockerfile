FROM python:3.6

ADD ./entrypoint.sh /entrypoint.sh
ADD ./main.py /main.py

ADD ./requirements.txt /requirements.txt
RUN pip install -q -r /requirements.txt

WORKDIR /
EXPOSE 9000
CMD [ "/entrypoint.sh" ]
