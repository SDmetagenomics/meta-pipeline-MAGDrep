FROM mambaorg/micromamba:1.5.8

LABEL org.opencontainers.image.title="meta-pipeline-MAGDrep"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Quality assessment and taxonomy of MAGs at scale"

COPY container/environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

COPY . /opt/meta-pipeline-MAGDrep
WORKDIR /opt/meta-pipeline-MAGDrep

RUN micromamba run -n base pip install -e . --no-deps

RUN chmod +x /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep && \
    ln -s /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep /usr/local/bin/meta-pipeline-MAGDrep

# Databases are mounted at runtime
VOLUME ["/databases"]
ENV MAGDREP_DB_DIR=/databases

ENTRYPOINT ["micromamba", "run", "-n", "base", "meta-pipeline-MAGDrep"]
CMD ["--help"]
