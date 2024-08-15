FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*


RUN curl -L https://fly.io/install.sh | sh

ENV PATH="/root/.fly/bin:${PATH}"

COPY . /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8000

CMD ["python", "/app/api.py"]