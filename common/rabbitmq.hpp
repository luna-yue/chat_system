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
#include "logger.hpp"

class MQClient
{
public:
    using MessageCallback = std::function<void(const char *, size_t)>;
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
        _channel->declareExchange(exchange, echange_type)
            .onError([](const char *message)
                     {
                    LOG_ERROR("声明交换机失败：{}", message);
                    exit(0); })
            .onSuccess([exchange]()
                       { LOG_ERROR("{} 交换机创建成功！", exchange); });
        _channel->declareQueue(queue)
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
        bool ret = _channel->publish(exchange, routing_key, msg);
        if (ret == false)
        {
            LOG_ERROR("{} 发布消息失败：", exchange);
            return false;
        }
        return true;
    }
    void consume(const std::string &queue, const MessageCallback &cb)
    {
        LOG_DEBUG("开始订阅 {} 队列消息！", queue);
        _channel->consume(queue, "consume-tag") // 返回值 DeferredConsumer
            .onReceived([this, cb](const AMQP::Message &message,
                                   uint64_t deliveryTag,
                                   bool redelivered)
                        {
                    cb(message.body(), message.bodySize());
                    _channel->ack(deliveryTag); })
            .onError([queue](const char *message)
                     {
                    LOG_ERROR("订阅 {} 队列消息失败: {}", queue, message);
                    exit(0); });
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
};