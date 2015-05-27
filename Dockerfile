FROM ubuntu:14.10
MAINTAINER Jukka Nousiainen <jukka.nousiainen@gmail.com>

RUN apt-get update && apt-get install -y lttng-tools liblttng-ust0 python
RUN lttng-relayd -d

ADD py/lttng-live.py /usr/local/bin/lttng-live

ENTRYPOINT ["python", "/usr/local/bin/lttng-live"]

EXPOSE 5342 5343 5344
