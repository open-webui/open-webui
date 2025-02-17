# source version
ARG version
# env, dev, test, prod
ARG env
# harbor host
ARG harbor
ARG service

FROM hub.p1.cn/cicd/lingualink_base:v1

COPY backend/requirements.txt /
RUN python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -U pip
RUN python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

ENV http_proxy="http://10.10.1.81:2345" \
    https_proxy="http://10.10.1.81:2345" \
    DATABASE_URL="pending" \
    VECTOR_DB="pgvector" \
    PGVECTOR_DB_URL="pending" \
    RAG_EMBEDDING_ENGINE="openai" \
    RAG_EMBEDDING_MODEL="text-embedding-3-small"

# RUN curl -O https://sqlite.org/2021/sqlite-autoconf-3350000.tar.gz && \
#     tar -xvzf sqlite-autoconf-3350000.tar.gz && \
#     cd sqlite-autoconf-3350000 && \
#     ./configure --prefix=/usr && \
#     make && \
#     make install && \
#     # 确保新安装的 sqlite3 覆盖旧版本
#     ln -sf /usr/bin/sqlite3 /usr/local/bin/sqlite3 && \
#     ln -sf /usr/lib/libsqlite3.so /usr/local/lib/libsqlite3.so && \
#     ln -sf /usr/lib/libsqlite3.so.0 /usr/local/lib/libsqlite3.so.0 && \
#     # 清理临时文件
#     cd .. && \
#     rm -rf sqlite-autoconf-3350000.tar.gz sqlite-autoconf-3350000


COPY . /
COPY deploy/backend/prod/entrypoint.sh /
RUN chmod +x /entrypoint.sh

WORKDIR /
ENTRYPOINT /bin/sh -c /entrypoint.sh