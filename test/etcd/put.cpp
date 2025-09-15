#include <etcd/Client.hpp>
#include <etcd/KeepAlive.hpp>
#include <etcd/Response.hpp>
#include <thread>
#include <string>
#include "../spdlog/logger.hpp"
using namespace std;
using namespace etcd;
int main()
{
   init_logger(false,string(),0);

    string etcd_host="http://127.0.0.1:2379";
    Client client(etcd_host);
    auto keep_alive=client.leasekeepalive(3).get();
    auto lease_id=keep_alive->Lease();
    auto resp1=client.put("/service/user","127.0.0.1:8080",lease_id).get();
    if(resp1.is_ok()==false)
    {
        LOG_ERROR("新增数据失败：{}",resp1.error_message());
        return -1;
    }
    auto resp2 =client.put("/service/friend","127.0.0.1:9000").get();
    if(resp2.is_ok()==false)
    {
        LOG_ERROR("新增数据失败：{}",resp2.error_message());
        return -1;
    }
    this_thread::sleep_for(chrono::seconds(10));
}