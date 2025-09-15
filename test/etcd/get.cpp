#include <etcd/Client.hpp>
#include <etcd/KeepAlive.hpp>
#include <etcd/Response.hpp>
#include <etcd/Watcher.hpp>
#include <etcd/Value.hpp>
#include<thread>
#include <string>
#include "../spdlog/logger.hpp"
using namespace std;
using namespace etcd;
void callback(const Response&resp)
{
    if(resp.is_ok()==false)
    {
        LOG_INFO("错误的事件通知 {}",resp.error_message());
    }
    for(auto const & ev :resp.events())
    {
        if(ev.event_type()==Event::EventType::PUT)
        {
          //键值对改变
          LOG_INFO("键值对改变");
          LOG_INFO("Current KEY:{} Current VAL {}",ev.kv().key(),ev.kv().as_string());
          LOG_INFO("PREV KEY:{} PREV VAL {}",ev.prev_kv().key(),ev.prev_kv().as_string());
        }
        else if(ev.event_type()==Event::EventType::DELETE_)
        {
            //键值对删除
          LOG_INFO("键值对删除");
          LOG_INFO("Current KEY:{} Current VAL {}",ev.kv().key(),ev.kv().as_string());
          LOG_INFO("PREV KEY:{} PREV VAL {}",ev.prev_kv().key(),ev.prev_kv().as_string());
        }
    }
}
int main()
{

   init_logger(false,string(),0);
   string etcd_host="http://127.0.0.1:2379";
   Client client(etcd_host);
   auto resp=client.ls("/service").get();
   if(resp.is_ok()==false)
   {
     LOG_ERROR("获取键值对数据失败：{}",resp.error_message());
   }
   int sz=resp.keys().size();
   for(int i=0;i<sz;i++)
   {
     LOG_INFO("{} 可以提供 {} 服务",resp.value(i).as_string(),resp.key(i));
   }
   auto watcher=Watcher(client,"/service",callback,true);
   watcher.Wait();
}