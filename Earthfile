build:
    FROM alpine:latest
    RUN apk add --update python3 py-pip gcc python3-dev libc-dev
    RUN apk add --no-cache build-base libffi-dev openssl-dev curl krb5-dev linux-headers zeromq-dev
    RUN pip3 install jinja2 flask flask_socketio netifaces
    WORKDIR /game
    COPY --dir static templates .
    COPY game.py .

run:
    LOCALLY
    WITH DOCKER --load llama:latest=+build
        RUN docker run --rm --network=host llama:latest python3 /game/game.py
    END
