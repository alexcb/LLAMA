deps:
    FROM alpine:latest
    RUN apk add --update python3 py-pip gcc python3-dev libc-dev
    RUN apk add --no-cache build-base libffi-dev openssl-dev curl krb5-dev linux-headers zeromq-dev
    WORKDIR /game
    COPY requirements.txt .
    RUN pip3 install -r requirements.txt

llama:
    FROM +deps
    COPY --dir static templates .
    COPY game.py .
    CMD ["python3", "/game/game.py"]
    SAVE IMAGE --push alexcb132/llama:latest

run:
    LOCALLY
    WITH DOCKER --load +llama
        RUN docker run --rm --network=host llama:latest python3 /game/game.py
    END
