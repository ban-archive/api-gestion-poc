FROM python:3.5

ENV PYTHONUNBUFFERED 1
EXPOSE 5959

RUN mkdir /src
WORKDIR /src

# Install wait-for-it
RUN curl --location --silent --show-error --fail \
    https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
    > /usr/local/bin/wait-for-it && \
    chmod +x /usr/local/bin/wait-for-it

# Install requirements before to speedup rebuild
ADD requirements.txt requirements-dev.txt /src/
RUN pip install -r requirements.txt -r requirements-dev.txt

# Add sources and perform initial install (can be overwritten by a volume)
ADD . /src/
RUN pip install -e .

# Always wait db to be ready
ENTRYPOINT ["/src/docker/entrypoint.sh"]

CMD ["/src/docker/run.sh"]
