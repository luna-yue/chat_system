#!/bin/bash
# 将宿主机上的预编译 C++ 库复制到项目目录，供 Docker 构建使用
# 运行一次即可：./scripts/prepare-deps.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPS_DIR="$PROJECT_DIR/docker-deps"

echo "=== 准备 Docker 依赖 ==="
rm -rf "$DEPS_DIR"
mkdir -p "$DEPS_DIR/lib" "$DEPS_DIR/include" "$DEPS_DIR/bin"

# 复制所有可能的 .so/.a 文件位置
echo "[1/6] 复制 /usr/local/lib/ ..."
cp -an /usr/local/lib/*.so* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/local/lib/lib*.a "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/local/lib/cmake "$DEPS_DIR/lib/cmake" 2>/dev/null || true

echo "[2/6] 复制 /usr/lib/ 特定库 ..."
cp -an /usr/lib/libodb* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/libamqpcpp* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/libboost* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/libcutl* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/libstudxml* "$DEPS_DIR/lib/" 2>/dev/null || true

echo "[3/6] 复制 /usr/lib/x86_64-linux-gnu/ 特定库 ..."
cp -an /usr/lib/x86_64-linux-gnu/libbrpc* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libetcd* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libleveldb* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libprotobuf* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libhiredis* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libssl* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libcrypto* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libcurl* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libz* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libdl* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libpthread* "$DEPS_DIR/lib/" 2>/dev/null || true
# libmysqlclient: 使用 Docker 自带的(apt installed)，不复制宿主机版本，避免 ABI 冲突
cp -an /usr/lib/x86_64-linux-gnu/libgrpc* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libgpr* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libabsl* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libboost* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libspdlog* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libfmt* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libgflags* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/lib/x86_64-linux-gnu/libcpprest* "$DEPS_DIR/lib/" 2>/dev/null || true

# 复制 /usr/local/include（所有自编译的头文件）
echo "[4/6] 复制 /usr/local/include/ ..."
cp -an /usr/local/include/* "$DEPS_DIR/include/" 2>/dev/null || true

# 复制 /usr/include 中的第三方库头文件
echo "[5/6] 复制 /usr/include 中的第三方库头文件 ..."
SYS_HEADERS="etcd brpc bthread butil bvar amqpcpp amqpcpp.h websocketpp odb spdlog fmt gflags leveldb hiredis jsoncpp json2pb libcutl libstudxml"
for h in $SYS_HEADERS; do
    if [ -e "/usr/include/$h" ]; then
        cp -an "/usr/include/$h" "$DEPS_DIR/include/" 2>/dev/null || true
    fi
done

# 复制 odb 编译器及其插件
echo "[6/6] 复制 odb 编译器及插件 ..."
cp /usr/bin/odb "$DEPS_DIR/bin/" 2>/dev/null || echo "  (odb 未安装, 跳过)"
cp /usr/bin/odb.so "$DEPS_DIR/bin/" 2>/dev/null || true
cp -an /usr/lib/libodb* "$DEPS_DIR/lib/" 2>/dev/null || true
cp -an /usr/local/lib/libbutl* "$DEPS_DIR/lib/" 2>/dev/null || true

echo ""
echo "=== 依赖复制完成 ==="
echo "目录: $DEPS_DIR"
du -sh "$DEPS_DIR"
echo ""
echo "现在可以运行: docker compose build"
