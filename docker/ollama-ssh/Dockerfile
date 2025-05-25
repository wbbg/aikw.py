FROM ollama/ollama:latest

ARG AUTHORIZED_KEYS_FILE

RUN apt-get update && apt-get install -y openssh-server && mkdir /var/run/sshd

COPY start.sh /usr/local/bin/start.sh
# RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# RUN echo 'root:ollama' | chpasswd
COPY ${AUTHORIZED_KEYS_FILE} /root/.ssh/authorized_keys

EXPOSE 22

ENTRYPOINT ["/usr/local/bin/start.sh"]
