#pragma once
//#include "etcd.hpp"
#include "logger.hpp"
#include <brpc/channel.h>
#include <mutex>
#include <string>
#include <vector>
#include <unordered_map>
#include <mutex>
using namespace std;
class ChannelManager
{
public:
    using ptr = shared_ptr<ChannelManager>;
    using ChannelPtr = shared_ptr<brpc::Channel>;
    vector<ChannelPtr> _channels;
    unordered_map<string, ChannelPtr> _hosts; // host 与 channel的映射
    string _service_name;
    int _index;
    std::mutex _mutex;
    ChannelManager(const string &service_name)
        : _service_name(service_name), _index(0) {}

    // 对某项服务上线一个节点 增加信道
    void append(const string &host)
    {
        ChannelPtr _channel = make_shared<brpc::Channel>();
        brpc::ChannelOptions opt;
        opt.protocol = "baidu_std";
        opt.timeout_ms = 100;
        opt.max_retry = 3;
        if (_channel->Init(host.c_str(), &opt) != 0)
        {
            LOG_ERROR("初始化{}-{}信道失败", _service_name, host);
        }
        _channels.push_back(_channel);
        std::unique_lock<std::mutex> lock(_mutex);
        _hosts[host] = _channel;
    }
    // 下线一个节点
    void remove(const string &host)
    {
        std::unique_lock<std::mutex> lock(_mutex);
        auto it = _hosts.find(host);
        if (it == _hosts.end())
        {
            LOG_WARN("{}-{}删除时未找到", _service_name, host);
            return;
        }
        for (int i = 0; i < _channels.size(); i++)
        {
            if (_channels[i] == it->second)
            {
                _channels.erase(_channels.begin() + i);
                break;
            }
        }
        _hosts.erase(it);
    }
    // 得到一个信道
    ChannelPtr choose()
    {
        std::unique_lock<std::mutex> lock(_mutex);
        if (_channels.size() == 0)
        {
            LOG_ERROR("当前没有提供{}服务的节点", _service_name);
        }
        int idx = _index++ % _channels.size();
        return _channels[idx];
    }
};
class ServiceManager
{
public:
    using ptr = shared_ptr<ServiceManager>;
    ChannelManager::ChannelPtr choose(const std::string &service_name)
    {
        std::unique_lock<std::mutex> lock(_mutex);
        auto sit = _services.find(service_name);
        if (sit == _services.end())
        {
            LOG_ERROR("当前没有能够提供 {} 服务的节点！", service_name);
            return ChannelManager::ChannelPtr();
        }
        return sit->second->choose();
    }
    // 先声明，我关注哪些服务的上下线，不关心的就不需要管理了
    void declared(const std::string &service_name)
    {
        std::unique_lock<std::mutex> lock(_mutex);
        _care_services.insert(service_name);
    }
    // 给etcd设置的回调 当有新服务上线或下线通知
    void onServiceOnline(const std::string &service_instance, const std::string &host)
    {
        std::string service_name = getServiceName(service_instance);
        ChannelManager::ptr service;
        {
            std::unique_lock<std::mutex> lock(_mutex);
            auto fit = _care_services.find(service_name);
            if (fit == _care_services.end())
            {
                LOG_DEBUG("{}-{} 服务上线了，但是当前并不关心！", service_name, host);
                return;
            }
            // 先获取管理对象，没有则创建，有则添加节点
            auto sit = _services.find(service_name);
            if (sit == _services.end())
            {
                service = std::make_shared<ChannelManager>(service_name);
                _services.insert(std::make_pair(service_name, service));
            }
            else
            {
                service = sit->second;
            }
        }
        if (!service)
        {
            LOG_ERROR("新增 {} 服务管理节点失败！", service_name);
            return;
        }
        service->append(host);
        LOG_DEBUG("{}-{} 服务上线新节点，进行添加管理！", service_name, host);
    }
    void onServiceOffline(const std::string &service_instance, const std::string &host)
    {
        std::string service_name = getServiceName(service_instance);
        ChannelManager::ptr service;
        {
            std::unique_lock<std::mutex> lock(_mutex);
            auto fit = _care_services.find(service_name);
            if (fit == _care_services.end())
            {
                LOG_DEBUG("{}-{} 服务下线了，但是当前并不关心！", service_name, host);
                return;
            }
            auto sit = _services.find(service_name);
            if (sit == _services.end())
            {
                LOG_WARN("删除{}服务节点时，没有找到管理对象", service_name);
                return;
            }
            service = sit->second;
        }
        service->remove(host);
        LOG_DEBUG("{}-{} 服务下线节点，进行删除管理！", service_name, host);
    }

private:
    std::string getServiceName(const std::string &service_instance)
    {
        auto pos = service_instance.find_last_of('/');
        if (pos == std::string::npos)
            return service_instance;
        return service_instance.substr(0, pos);
    }
    std::mutex _mutex;
    std::unordered_set<std::string> _care_services;
    std::unordered_map<std::string, ChannelManager::ptr> _services;
};