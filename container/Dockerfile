FROM mambaorg/micromamba:1.5.8

LABEL org.opencontainers.image.title="meta-pipeline-MAGDrep"
LABEL org.opencontainers.image.version="1.3.0"
LABEL org.opencontainers.image.description="Quality assessment, taxonomy, and dereplication of MAGs at scale"

COPY . /opt/meta-pipeline-MAGDrep
WORKDIR /opt/meta-pipeline-MAGDrep

# Main env: CheckM2 + GTDB-Tk + skani + SeqKit + Snakemake + pipeline code
COPY environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

RUN micromamba run -n base pip install -e . --no-deps

# Side env: CheckM1 (Python-incompatible with CheckM2, so sibling env)
COPY envs/checkm1.yml /tmp/checkm1.yml
RUN micromamba create -y -n magdrep-checkm1 -f /tmp/checkm1.yml && \
    micromamba clean --all --yes

RUN chmod +x /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep && \
    ln -s /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep /usr/local/bin/meta-pipeline-MAGDrep

# Databases are mounted at runtime
VOLUME ["/databases"]
ENV MAGDREP_DB_DIR=/databases

ENTRYPOINT ["micromamba", "run", "-n", "base", "meta-pipeline-MAGDrep"]
CMD ["--help"]
