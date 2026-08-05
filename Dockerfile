# ============================================================
# Stage 1: Builder — 只编译项目本身
# (依赖库从宿主机 /usr/local 复制)
# ============================================================
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# ---- 系统构建工具 ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake \
    libprotobuf-dev libprotoc-dev protobuf-compiler \
    libgflags-dev libspdlog-dev libfmt-dev \
    libleveldb-dev libssl-dev libcurl4-openssl-dev \
    libcpprest-dev libboost-all-dev \
    libhiredis-dev libev-dev \
    libmysqlclient-dev \
    libgrpc++-dev libgrpc-dev protobuf-compiler-grpc \
    ca-certificates \
    && apt-get clean

# ---- 从宿主机复制预编译的第三方库 ----
# 需要先运行: ./scripts/prepare-deps.sh
COPY docker-deps/lib/ /usr/local/lib/
COPY docker-deps/include/ /usr/local/include/
COPY docker-deps/bin/ /usr/bin/

RUN ldconfig

# ---- 编译本项目 ----
WORKDIR /src
COPY . .

RUN mkdir -p build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
       -DCMAKE_CXX_STANDARD_LIBRARIES="-lmysqlclient -L/usr/local/lib" \
    && make -j$(nproc)

# ============================================================
# Stage 2: Runtime — 最小运行时
# ============================================================
FROM ubuntu:22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libprotobuf23 libleveldb1d libcurl4 libssl3 \
    libboost-system1.74 libboost-date-time1.74 libboost-thread1.74 \
    libmysqlclient21 libhiredis0.14 libev4 \
    libc-ares2 libfmt8 \
    && apt-get clean \
    && ln -sf /usr/lib/x86_64-linux-gnu/libmysqlclient.so.21 /usr/lib/x86_64-linux-gnu/libmysqlclient-21.so

# 从 builder 复制所有运行时库
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/include/ /usr/local/include/

# 复制编译好的二进制
COPY --from=builder /src/build/user/user_server /app/
COPY --from=builder /src/build/file/file_server /app/
COPY --from=builder /src/build/speech/speech_server /app/
COPY --from=builder /src/build/transmite/transmite_server /app/
COPY --from=builder /src/build/message/message_server /app/
COPY --from=builder /src/build/friend/friend_server /app/
COPY --from=builder /src/build/gateway/gateway_server /app/
COPY --from=builder /src/build/es_store/es_store_server /app/

# 复制入口脚本
COPY scripts/entrypoint.sh /app/

RUN ldconfig && chmod +x /app/entrypoint.sh
WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
