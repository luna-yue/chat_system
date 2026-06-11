#include "es_store_server.hpp"

DEFINE_bool(run_mode, false, "程序的运行模式，false-调试； true-发布；");
DEFINE_string(log_file, "", "发布模式下，用于指定日志的输出文件");
DEFINE_int32(log_level, 0, "发布模式下，用于指定日志输出等级");

DEFINE_string(es_host, "http://127.0.0.1:9200/", "ES搜索引擎服务器URL");

DEFINE_string(mq_user, "root", "消息队列服务器访问用户名");
DEFINE_string(mq_pswd, "123456", "消息队列服务器访问密码");
DEFINE_string(mq_host, "127.0.0.1:5672", "消息队列服务器访问地址");
DEFINE_string(mq_msg_exchange, "msg_exchange", "持久化消息的发布交换机名称");
DEFINE_string(mq_msg_queue, "msg_queue_es", "持久化消息的发布队列名称");
DEFINE_string(mq_msg_binding_key, "msg.text", "持久化消息的发布队列名称");

int main(int argc, char *argv[])
{
    google::ParseCommandLineFlags(&argc, &argv, true);
    init_logger(FLAGS_run_mode, FLAGS_log_file, FLAGS_log_level);

    luna::EsStoreServerBuilder esb;
    esb.make_mq_object(FLAGS_mq_user, FLAGS_mq_pswd, FLAGS_mq_host,
        FLAGS_mq_msg_exchange, FLAGS_mq_msg_queue, FLAGS_mq_msg_binding_key);
    esb.make_es_object({FLAGS_es_host});
    auto server = esb.build(FLAGS_mq_msg_exchange,FLAGS_mq_msg_binding_key);
    server->start();
    
}