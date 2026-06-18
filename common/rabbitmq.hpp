// 封装一个 MQClient：
// 提供声明指定交换机与队列，并进行绑定的功能；
// 提供向指定交换机发布消息的功能
// 提供订阅指定队列消息，并设置回调函数进行消息消费处理的功能
#pragma once
#include <ev.h>
#include <amqpcpp.h>
#include <amqpcpp/libev.h>
#include <openssl/ssl.h>
#include <openssl/opensslv.h>
#include <iostream>
#include <functional>
#include <mutex>
#include "logger.hpp"
namespace luna
{
    enum class ConsumeResult
    {
        Success, // 成功
        Retry,   // 可重试错误
        Fatal    // 致命错误
    };
    class MQClient
    {
    public:
        using MessageCallback = std::function<ConsumeResult(const char *, size_t)>;
        using ptr = std::shared_ptr<MQClient>;
        MQClient(const std::string &user,
                 const std::string passwd,
                 const std::string host)
        {
            _loop = EV_DEFAULT;
            _handler = std::make_unique<AMQP::LibEvHandler>(_loop);
            // amqp://root:123456@127.0.0.1:5672/
            std::string url = "amqp://" + user + ":" + passwd + "@" + host + "/";
            AMQP::Address address(url);
            _connection = std::make_unique<AMQP::TcpConnection>(_handler.get(), address);
            _channel = std::make_unique<AMQP::TcpChannel>(_connection.get());
            _channel->confirmSelect()
                .onSuccess([]()
                           { LOG_INFO("confirm模式开启成功"); })
                .onAck([](uint64_t tag, bool multiple)
                       { LOG_INFO("消息确认成功 tag={}", tag); })
                .onNack([](uint64_t tag,
                           bool multiple,
                           bool requeue)
                        {
                            LOG_ERROR(
                                "消息确认失败 tag={} requeue={}",
                                tag,
                                requeue);

                            // TODO: 
                            // 写本地日志
                            // 放重试队列
                            // 重新publish
                            
                        });
            // 因为ev_run需要执行循环 肯定不能在主线程执行需要创一个子线程
            _loop_thread = std::thread([this]()
                                       { ev_run(_loop, 0); });
        }
        ~MQClient()
        {
            // 直接在主线程中关闭ev可能导致两个线程同时访问loop，线程不安全
            // 用向watcher描述符写入触发读事件，随后在回调中关闭ev
            ev_async_init(&_async_watcher, watcher_callback);
            ev_async_start(_loop, &_async_watcher);
            ev_async_send(_loop, &_async_watcher);
            _loop_thread.join();
            _loop = nullptr;
        }
        void declareComponents(const std::string &exchange,
                               const std::string &queue,
                               const std::string &routing_key = "routing_key",
                               AMQP::ExchangeType echange_type = AMQP::ExchangeType::direct)
        {
            _channel->declareExchange(exchange, echange_type, AMQP::durable)
                .onError([](const char *message)
                         {
                    LOG_ERROR("声明交换机失败：{}", message);
                    exit(0); })
                .onSuccess([exchange]()
                           { LOG_ERROR("{} 交换机创建成功！", exchange); });
            _channel->declareQueue(queue, AMQP::durable)
                .onError([](const char *message)
                         {
                    LOG_ERROR("声明队列失败：{}", message);
                    exit(0); })
                .onSuccess([queue]()
                           { LOG_ERROR("{} 队列创建成功！", queue); });
            _channel->bindQueue(exchange, queue, routing_key)
                .onError([exchange, queue](const char *message)
                         {
                    LOG_ERROR("{} - {} 绑定失败：", exchange, queue);
                    exit(0); })
                .onSuccess([exchange, queue, routing_key]()
                           { LOG_ERROR("{} - {} - {} 绑定成功！", exchange, queue, routing_key); });
        }
        bool publish(const std::string &exchange,
                     const std::string &msg,
                     const std::string &routing_key = "routing_key")
        {
            LOG_DEBUG("向交换机 {}-{} 发布消息！", exchange, routing_key);
            std::lock_guard<std::mutex> lock(publish_mutex);
            bool ret = _channel->publish(exchange, routing_key, msg);
            if (ret == false)
            {
                LOG_ERROR("{} 发布消息失败：", exchange);
                return false;
            }
            return true;
        }
        bool publish(const std::string &exchange,
                     const AMQP::Envelope &env,
                     const std::string &routing_key = "routing_key")
        {
            LOG_DEBUG("向交换机 {}-{} 发布消息！", exchange, routing_key);
            std::lock_guard<std::mutex> lock(publish_mutex);
            bool ret = _channel->publish(exchange, routing_key, env);
            if (ret == false)
            {
                LOG_ERROR("{} 发布消息失败：", exchange);
                return false;
            }
            return true;
        }
        std::string buildBody(int retry_count, const std::string &payload)
        {
            return std::to_string(retry_count) + "|" + payload;
        }
        void consume(const std::string &queue, const MessageCallback &cb, const std::string &exchange_name, const std::string &routing_key)
        {
            LOG_DEBUG("开始订阅 {} 队列消息！", queue);
            _channel->consume(queue, "consume-tag") // 返回值 DeferredConsumer
                .onReceived([this, cb, exchange_name, routing_key](const AMQP::Message &message,
                                                                   uint64_t deliveryTag,
                                                                   bool redelivered)
                            {
                std::string body(message.body(), message.bodySize());

                int retry_count = 0;
                std::string payload;

                // 1. 找分隔符 |
                size_t pos = body.find('|');

                if (pos != std::string::npos)
                {
                    retry_count = std::stoi(body.substr(0, pos));
                    payload = body.substr(pos + 1);
                }
                else
                {
                    // 兼容旧消息（没有 retry_count）
                    payload = body;
                }

                // 2. 只把 payload 交给业务回调
                ConsumeResult result = cb(payload.data(), payload.size());

                if (result == ConsumeResult::Success)
                {
                    _channel->ack(deliveryTag);
                    return;
                }

                if (result == ConsumeResult::Retry)
                {
                    retry_count++;

                    if (retry_count > 5)
                    {
                        LOG_ERROR("超过最大重试次数，丢弃消息 | msg_body:=", payload);
                        _channel->ack(deliveryTag);
                        return;
                    }
                    std::string new_body = buildBody(retry_count, payload);
                    AMQP::Envelope env(new_body.data(), new_body.size());

                    env.setDeliveryMode(2);
                    _channel->publish(exchange_name, routing_key, env);
                    _channel->ack(deliveryTag);
                    return;
                }

                if (result == ConsumeResult::Fatal)
                {
                    _channel->ack(deliveryTag);
                    LOG_ERROR("Fatal消息丢弃 | msg_body:=", message.body());
                    return;
                }

                _channel->ack(deliveryTag);
                LOG_ERROR("未知状态，默认丢弃"); })
                .onError([queue](const char *message)
                         {
                    LOG_ERROR("订阅 {} 队列消息失败: {}", queue, message);
                    exit(0); })
                .onSuccess([]()
                           { LOG_DEBUG("consume 注册成功:"); });
            _channel->onError([](const char *msg)
                              { LOG_ERROR("channel error: {}", msg); });
        }

    private:
        static void watcher_callback(struct ev_loop *loop, ev_async *watcher, int32_t revents)
        {
            ev_break(loop, EVBREAK_ALL);
        }
        struct ev_async _async_watcher;
        struct ev_loop *_loop;
        std::unique_ptr<AMQP::LibEvHandler> _handler;
        std::unique_ptr<AMQP::TcpConnection> _connection;
        std::unique_ptr<AMQP::TcpChannel> _channel;
        std::thread _loop_thread;

        std::mutex publish_mutex;
    };
}