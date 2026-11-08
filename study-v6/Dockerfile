FROM openrsi-asset-generator:v5
COPY wheels /wheels-v6
RUN PYTHONPATH=/wheels-v6/pip-25.0.1-py3-none-any.whl python3 -m pip install --no-index --find-links=/wheels-v6 --target=/opt/proxy --no-deps --no-compile trimesh==4.12.2 coacd==1.0.14 fast-simplification==0.2.0 rtree==1.4.1 networkx==3.5
ENV PYTHONPATH=/opt/proxy:/opt/study PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN python3 -c "import coacd,fast_simplification,rtree,trimesh,networkx;print('V6 CPU dependencies available')"
