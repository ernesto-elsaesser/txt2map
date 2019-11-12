FROM python:3.8-slim
RUN pip install requests nltk
WORKDIR /map2txt
ADD . /map2txt
RUN python install.py
EXPOSE 80
ENTRYPOINT ["python", "server.py"]