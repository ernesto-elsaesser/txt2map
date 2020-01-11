FROM openjdk:8

WORKDIR /t2mcc

ADD ./load-deps.sh load.sh
RUN ./load.sh

ADD . .
RUN ./build.sh

EXPOSE 80
ENTRYPOINT ./run.sh 80