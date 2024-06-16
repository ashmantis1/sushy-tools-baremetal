FROM python:3.12-bookworm as builder


USER 0
RUN mkdir /build

ADD ./requirements.txt /build
ADD setup.py /build
add setup.cfg /build
ADD README.rst /build
ADD sushy_tools /build/sushy_tools

RUN  python3 -m venv /opt/venv 
ENV PATH="/opt/venv/bin:$PATH"
ENV PBR_VERSION=1.2.3

WORKDIR /build
RUN pip3 install -r requirements.txt && pip3 install gunicorn && \
    python3 setup.py install

FROM python:3.12-bookworm as runner 
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/sushy_tools /sushy_tools
run mkdir /config && \ 
    useradd runner && \ 
    chown -R runner:runner /config && \ 
    apt update && apt -y install iputils-ping

#USER runner 
WORKDIR /config
ENV SUSHY_EMULATOR_BIND_PORT=8000
ENV PATH="/opt/venv/bin:$PATH"
ENV SUSHY_EMULATOR_CONFIG=/config/conf
EXPOSE 80
ENTRYPOINT ["gunicorn", "-b 0.0.0.0:80", "--chdir", "/sushy_tools/emulator", "main:app"]


    

