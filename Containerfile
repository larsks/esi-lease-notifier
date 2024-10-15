FROM docker.io/alpine:latest

RUN apk add python3 py3-pip py3-netifaces

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m venv --system-site-packages .venv
RUN . .venv/bin/activate && pip install -r requirements.txt
COPY . ./
RUN . .venv/bin/activate && pip install .

CMD ["crond", "-f", "-L", "/dev/stderr"]
