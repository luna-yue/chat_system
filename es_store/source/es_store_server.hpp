#pragma once
#include <butil/logging.h>
#include <gflags/gflags.h>
#include "data_es.hpp"
#include "logger.hpp"
#include "utils.hpp"
#include "rabbitmq.hpp"
#include "base.pb.h" // protobuf框架代码
namespace luna
{
    class EsStoreServer
    {
    public:
        using ptr = std::shared_ptr<EsStoreServer>;

        EsStoreServer(
            const MQClient::ptr &mq_client,
            const std::shared_ptr<elasticlient::Client> &es_client,
            const std::string &queue_name,
            const std::string &exchange_name,
            const std::string &routing_key)
            : _mq_client(mq_client),
              _es_client(es_client),
              _queue_name(queue_name),
              _es_message(std::make_shared<ESMessage>(es_client)),
              _exchange_name(exchange_name),
              _routing_key(routing_key)
        {
            _es_message->createIndex();
        }

        ~EsStoreServer() {}

    public:
        ConsumeResult onMessage(
            const char *body,
            size_t sz)
        {
            LOG_DEBUG("收到ES存储消息");

            // TODO:
            // protobuf反序列化
            // 写入ES
            // 返回 Success / Retry / Fatal
            LOG_DEBUG("(ES)收到新消息，进行存储处理！");
            // 1. 取出序列化的消息内容，进行反序列化
            luna::MessageInfo message;
            bool ret = message.ParseFromArray(body, sz);
            if (ret == false)
            {
                LOG_ERROR("对消费到的消息进行反序列化失败！");
                return luna::ConsumeResult::Fatal;
            }
            if (message.message().message_type() != MessageType::STRING)
            {
                return ConsumeResult::Fatal;
            }
            //  1. 如果是一个文本类型消息，取元信息存储到ES中

            std::string content = message.message().string_message().content();
            ret = _es_message->appendData(
                message.sender().user_id(),
                message.message_id(),
                message.timestamp(),
                message.chat_session_id(),
                content);
            if (ret == false)
            {
                LOG_ERROR("文本消息向存储引擎进行存储失败！");
                return luna::ConsumeResult::Retry;
            }
            
            return ConsumeResult::Success;
        }

        void start()
        {
            auto callback =
                std::bind(
                    &EsStoreServer::onMessage,
                    this,
                    std::placeholders::_1,
                    std::placeholders::_2);

            _mq_client->consume(
                _queue_name,
                callback,_exchange_name,_routing_key);

            LOG_INFO("ES Store Server 启动成功");

            while (true)
            {
                sleep(1);
            }
        }

    private:
        MQClient::ptr _mq_client;
        std::shared_ptr<elasticlient::Client>
            _es_client;
        std::string _queue_name;
        ESMessage::ptr _es_message;
        std::string _exchange_name;
        std::string _routing_key;
    };

    class EsStoreServerBuilder
    {
    public:
        void make_es_object(
            const std::vector<std::string> &host_list)
        {
            _es_client =
                ESClientFactory::create(host_list);
        }

        void make_mq_object(
            const std::string &user,
            const std::string &passwd,
            const std::string &host,
            const std::string &exchange_name,
            const std::string &queue_name,
            const std::string &binding_key)
        {
            _queue_name = queue_name;

            _mq_client =
                std::make_shared<MQClient>(
                    user,
                    passwd,
                    host);

            _mq_client->declareComponents(
                exchange_name,
                queue_name,
                binding_key,
                AMQP::topic);
        }
        EsStoreServer::ptr build(const std::string&exchange_name,const std::string & routing_key)
        {
            return std::make_shared<EsStoreServer>(
                _mq_client,
                _es_client,
                _queue_name,exchange_name,routing_key);
        }

    private:
        std::shared_ptr<elasticlient::Client>
            _es_client;
        MQClient::ptr _mq_client;
        std::string _queue_name;
    };
}