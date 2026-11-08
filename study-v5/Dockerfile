# Local CPU prototype extends the already validated Blender/Python base.
# Build environment/Dockerfile as openrsi-asset-blender:pilot-v0 first.
# Builder verifies the existing base image ID; every run pins the final image ID.
FROM openrsi-asset-blender:pilot-v0
COPY wheels /wheels
RUN PYTHONPATH=/wheels/pip-25.0.1-py3-none-any.whl python3 -m pip install --no-index --find-links=/wheels --target=/opt/study --no-compile numpy==2.4.4 scipy==1.17.1 python-fcl==0.7.0.11
ENV PYTHONPATH=/opt/study PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /work
RUN python3 -c "import numpy,scipy,fcl;print(numpy.__version__,scipy.__version__)"
