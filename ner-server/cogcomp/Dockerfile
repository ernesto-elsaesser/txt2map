FROM openjdk:8

WORKDIR /t2mcc
ADD ./load-deps.sh load-deps.sh
RUN ./load-deps.sh

ADD ./CogCompServer.java CogCompServer.java
ADD ./ner.properties ner.properties
ADD ./build.sh build.sh
RUN ./build.sh

ENV CLASSPATH="/t2mcc:/t2mcc/lib/*"
EXPOSE 80
ENTRYPOINT java -Xmx2g CogCompServer 80