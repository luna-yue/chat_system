#!/bin/bash
# 通用启动脚本 — 根据 SERVICE_NAME 选择二进制，其余参数通过环境变量传入
set -e

SERVICE_BIN="${SERVICE_NAME}_server"

# ---- 公共参数 ----
# 默认：stdout 模式（Docker 采集，docker compose logs -f 可见）
# 可选：LOG_MODE=file → 写文件（需挂载 volume 持久化）
if [ "${LOG_MODE}" = "file" ]; then
    COMMON_ARGS=(
        --run_mode=true
        --log_file="/app/logs/${SERVICE_NAME}_server.log"
        --log_level=3
    )
else
    COMMON_ARGS=(
        --run_mode=false
        --log_file=""
        --log_level=0
    )
fi

# ---- 根据服务类型拼接特定参数 ----
case "$SERVICE_NAME" in

user)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/user_service/instance}"
        --access_host="${ACCESS_HOST:-user:10003}"
        --listen_port="${LISTEN_PORT:-10003}"
        --mysql_host="${MYSQL_HOST:-mysql}"
        --mysql_user="${MYSQL_USER:-root}"
        --mysql_pswd="${MYSQL_PSWD:-968745321}"
        --mysql_db="${MYSQL_DB:-TestDB}"
        --mysql_port="${MYSQL_PORT:-3306}"
        --redis_host="${REDIS_HOST:-redis}"
        --es_host="http://${ES_HOST:-elasticsearch}:9200/"
        --machine_id="${MACHINE_ID:-1}"
    )
    ;;

friend)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/friend_service/instance}"
        --access_host="${ACCESS_HOST:-friend:10006}"
        --listen_port="${LISTEN_PORT:-10006}"
        --mysql_host="${MYSQL_HOST:-mysql}"
        --mysql_user="${MYSQL_USER:-root}"
        --mysql_pswd="${MYSQL_PSWD:-968745321}"
        --mysql_db="${MYSQL_DB:-TestDB}"
        --mysql_port="${MYSQL_PORT:-3306}"
        --es_host="http://${ES_HOST:-elasticsearch}:9200/"
    )
    ;;

transmite)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/transmite_service/instance}"
        --access_host="${ACCESS_HOST:-transmite:10004}"
        --listen_port="${LISTEN_PORT:-10004}"
        --mysql_host="${MYSQL_HOST:-mysql}"
        --mysql_user="${MYSQL_USER:-root}"
        --mysql_pswd="${MYSQL_PSWD:-968745321}"
        --mysql_db="${MYSQL_DB:-TestDB}"
        --mysql_port="${MYSQL_PORT:-3306}"
        --mq_host="${MQ_HOST:-rabbitmq}:5672"
        --mq_msg_exchange="${MQ_EXCHANGE:-msg_exchange}"
        --mq_msg_queue="${MQ_QUEUE:-msg_queue}"
        --mq_msg_binding_key="${MQ_BINDING_KEY:-msg.#}"
        --redis_host="${REDIS_HOST:-redis}"
        --machine_id="${MACHINE_ID:-1}"
    )
    ;;

message)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/message_service/instance}"
        --access_host="${ACCESS_HOST:-message:10005}"
        --listen_port="${LISTEN_PORT:-10005}"
        --mysql_host="${MYSQL_HOST:-mysql}"
        --mysql_user="${MYSQL_USER:-root}"
        --mysql_pswd="${MYSQL_PSWD:-968745321}"
        --mysql_db="${MYSQL_DB:-TestDB}"
        --mysql_port="${MYSQL_PORT:-3306}"
        --es_host="http://${ES_HOST:-elasticsearch}:9200/"
        --mq_host="${MQ_HOST:-rabbitmq}:5672"
        --mq_msg_exchange="${MQ_EXCHANGE:-msg_exchange}"
        --mq_msg_queue="${MQ_QUEUE:-msg_queue_mysql}"
        --mq_msg_binding_key="${MQ_BINDING_KEY:-msg.#}"
    )
    ;;

es_store)
    COMMON_ARGS+=(
        --es_host="http://${ES_HOST:-elasticsearch}:9200/"
        --mq_host="${MQ_HOST:-rabbitmq}:5672"
        --mq_msg_exchange="${MQ_EXCHANGE:-msg_exchange}"
        --mq_msg_queue="${MQ_QUEUE:-msg_queue_es}"
        --mq_msg_binding_key="${MQ_BINDING_KEY:-msg.text}"
    )
    ;;

file)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/file_service/instance}"
        --access_host="${ACCESS_HOST:-file:10002}"
        --listen_port="${LISTEN_PORT:-10002}"
        --storage_path="${STORAGE_PATH:-./data/}"
    )
    ;;

speech)
    COMMON_ARGS+=(
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --instance_name="${INSTANCE_NAME:-/speech_service/instance}"
        --access_host="${ACCESS_HOST:-speech:10001}"
        --listen_port="${LISTEN_PORT:-10001}"
    )
    ;;

gateway)
    COMMON_ARGS+=(
        --http_listen_port="${HTTP_PORT:-9000}"
        --websocket_listen_port="${WS_PORT:-9001}"
        --registry_host="http://${ETCD_HOST:-etcd}:2379"
        --redis_host="${REDIS_HOST:-redis}"
    )
    ;;

*)
    echo "ERROR: Unknown SERVICE_NAME=$SERVICE_NAME"
    exit 1
    ;;
esac

echo "Starting $SERVICE_BIN with args: ${COMMON_ARGS[*]}"
exec "/app/$SERVICE_BIN" "${COMMON_ARGS[@]}"
