FROM debian:jessie

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install PyMySQL==0.6.7

# Install woof
COPY build/woof.tar.gz ./
RUN tar -xaf woof.tar.gz && cd woof && python3 setup.py install && cd ../

COPY build/demo.tar.gz ./
RUN tar -xaf demo.tar.gz

COPY launch_server.sh ./

CMD ["/bin/bash", "launch_server.sh"]
