#pragma once
#include <etcd/Client.hpp>
#include <etcd/KeepAlive.hpp>
#include <etcd/Response.hpp>
#include <etcd/Watcher.hpp>
#include <thread>
#include <string>
#include <functional>
#include "logger.hpp"
using namespace std;
using namespace etcd;
// 服务注册 //put 设置回调
class Registry
{
public:
    using ptr=shared_ptr<Registry>;
    Registry(const string &host) : _client(make_shared<Client>(host)),
                                   _keepalive(_client->leasekeepalive(3).get()),
                                   _lease_id(_keepalive->Lease())
    {
    }
    ~Registry() { _keepalive->Cancel(); }
    bool Registr(const string &key, const string &val)
    {
        auto resp = _client->put(key, val, _lease_id).get();
        if (!resp.is_ok())
        {
            LOG_ERROR("服务注册失败 {}", resp.error_message());
            return false;
        }
        return true;
    }

private:
    shared_ptr<Client> _client;
    shared_ptr<KeepAlive> _keepalive; 
    uint64_t _lease_id;

};
// 用于服务发现 get 调用回调 需要有服务上线和服务下线两个回调
class Discovery
{
    
public:
    using NotifyCallback = function<void(string, string)>;
    using ptr=shared_ptr<Discovery>;
    Discovery(const string &host,
              const string &base_dir,
              const NotifyCallback put_cb,
              const NotifyCallback del_cb) : _client(make_shared<Client>(host)),
                                             _put_cb(put_cb), _del_cb(del_cb)
    {
        auto resp = _client->ls(base_dir).get();
        if (!resp.is_ok())
        {
            LOG_ERROR("获取服务信息失败 {}", resp.error_message());
        }
        int sz = resp.keys().size();
        for (int i = 0; i < sz; i++)
        {
            // 这里调用上线回调是为了通知使用服务发现者当前已经存在的服务
            if (_put_cb)
                _put_cb(resp.key(i), resp.value(i).as_string());
        }
        _watcher = make_shared<Watcher>(*_client, base_dir,
                                        bind(&Discovery::Dispatcher, this, placeholders::_1), true);
    }

private:
    void Dispatcher(const Response & resp)
    {
        if (!resp.is_ok())
        {
            LOG_ERROR("接收到一个错误的事件通知 {}", resp.error_message());
            return;
        }
        for (auto const &ev : resp.events())
        {
            if (ev.event_type() == Event::EventType::PUT)
            {
                if(_put_cb)_put_cb(ev.kv().key(),ev.kv().as_string());
                LOG_INFO("新增服务 Current KEY:{} Current VAL {}", ev.kv().key(), ev.kv().as_string());
            }
            else if (ev.event_type() == Event::EventType::DELETE_)
            {
                if(_del_cb)_del_cb(ev.prev_kv().key(),ev.prev_kv().as_string());
                LOG_INFO("服务下线 PREV KEY:{} PREV VAL {}”, ev.prev_kv().key(), ev.prev_kv().as_string()");
            }
        }
    }
    shared_ptr<Client> _client;
    shared_ptr<Watcher> _watcher;
    NotifyCallback _put_cb;
    NotifyCallback _del_cb;
};