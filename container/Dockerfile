FROM mambaorg/micromamba:1.5.8

LABEL org.opencontainers.image.title="meta-pipeline-MAGQC"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Quality assessment and taxonomy of MAGs at scale"

COPY container/environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

COPY . /opt/meta-pipeline-MAGQC
WORKDIR /opt/meta-pipeline-MAGQC

RUN micromamba run -n base pip install -e . --no-deps

RUN chmod +x /opt/meta-pipeline-MAGQC/meta-pipeline-MAGQC && \
    ln -s /opt/meta-pipeline-MAGQC/meta-pipeline-MAGQC /usr/local/bin/meta-pipeline-MAGQC

# Databases are mounted at runtime
VOLUME ["/databases"]
ENV MAGQC_DB_DIR=/databases

ENTRYPOINT ["micromamba", "run", "-n", "base", "meta-pipeline-MAGQC"]
CMD ["--help"]
