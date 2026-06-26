# syntax=docker/dockerfile:1.7
#
# Commit-image Dockerfile (SMALL form) for mathandy/svgpathtools — builds ON TOP of the org base
# image (ghcr.io/mayhemheroes/base), which provides debian + clang/llvm + Python 3.13 + the build
# identities + the build-contract ENV.
#
# This is a Python (Atheris) target. The base has no PyPI deps, so we bake a WHEELHOUSE here (online,
# once) and mayhem/build.sh installs from it with --no-index — so the air-gapped PATCH re-run
# (docker run --network none ... bash mayhem/build.sh) never reaches the network (SPEC §6.5).
#
# Build (from the repo root):
#   DOCKER_BUILDKIT=1 docker build -f mayhem/Dockerfile \
#       --build-arg COMMIT=$(git rev-parse HEAD) -t svgpathtools-commit:test .

FROM ghcr.io/mayhemheroes/base:20260621

ARG COMMIT
ARG REPO_URL
# SOURCE_DATE_EPOCH stays an ARG (available to build.sh); never bake it as ENV — an empty value
# breaks clang. build.sh unsets it when empty.
ARG SOURCE_DATE_EPOCH
# Sanitizer override: declared WITHOUT a default so an unset arg lets the base ENV flow through.
ARG SANITIZER_FLAGS

# ── Bake the Python wheelhouse (ONLINE, root) so build.sh installs OFFLINE (air-gapped re-run) ──────
# atheris is the fuzzing engine; setuptools is svgpathtools' build backend; numpy/scipy/svgwrite are
# its runtime dependencies (see setup.py install_requires) — needed to import the harnessed package.
ENV WHEELHOUSE=/opt/toolchains/python/wheelhouse
USER root
RUN mkdir -p "$WHEELHOUSE" && \
    python3 -m pip download --dest "$WHEELHOUSE" \
        'atheris==3.1.0' 'setuptools>=61' 'wheel' \
        'numpy' 'scipy' 'svgwrite' && \
    chmod -R a+rX /opt/toolchains
USER mayhem

# Source enters from the build CONTEXT (the CI checkout): the FULL repo (incl. .git history) is
# copied to /mayhem; build.sh builds in place.
WORKDIR /mayhem
COPY --chown=2000:2000 . /mayhem

RUN bash mayhem/build.sh

# Run the behavioral oracle at build time (a failing suite fails the image build).
RUN if [ -f mayhem/test.sh ]; then bash mayhem/test.sh; else echo "no mayhem/test.sh"; fi

LABEL org.opencontainers.image.source="${REPO_URL}" \
      org.opencontainers.image.revision="${COMMIT}" \
      rlenv.tier="commit" \
      rlenv.source_date_epoch="${SOURCE_DATE_EPOCH}" \
      rlenv.user="mayhem"

USER mayhem
WORKDIR /mayhem
