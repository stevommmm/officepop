FROM python:3.6

ADD ./requirements.txt /requirements.txt
RUN pip install -q -r /requirements.txt

ADD ./entrypoint.sh /entrypoint.sh
ADD ./main.py /main.py

WORKDIR /
EXPOSE 9000
CMD [ "/entrypoint.sh" ]
