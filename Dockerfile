FROM python:3.8.8-slim-buster

RUN echo "- install packages -" && \
    apt-get update && \
    apt-get install -y git && \
    pip install pipenv

RUN echo "- create user and folders and download it -" && \
    mkdir -p /app /home/abc && \
    useradd -d /home/abc abc && \
    git clone https://github.com/yannickgloster/discord-10man.git /app/discord && \
    chown -R abc:abc /home/abc /app

RUN echo "- cleanups -" && \
    apt-get remove -y git && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf \
	/tmp/* \
	/var/lib/apt/lists/* \
	/var/tmp/*

USER abc
WORKDIR /app/discord

RUN echo "- install dependencies -" && \
    pipenv install

CMD [ "pipenv", "run", "python3", "run.py" ]
