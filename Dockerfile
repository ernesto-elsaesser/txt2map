FROM python:3.8
RUN pip install requests regex
WORKDIR /map2txt
ADD . /map2txt
EXPOSE 80
ENTRYPOINT ["python", "server.py"]