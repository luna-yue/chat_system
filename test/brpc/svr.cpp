#include <brpc/server.h>
#include <butil/logging.h>
#include "../../common/logger.hpp"
#include "echo.pb.h"

//1. 继承于EchoService创建一个子类，并实现rpc调用的业务功能
class EchoServiceImpl : public example::EchoService {
    public:
        EchoServiceImpl(){}
        ~EchoServiceImpl(){}
        void Echo(google::protobuf::RpcController* controller,
                       const ::example::EchoRequest* request,
                       ::example::EchoResponse* response,
                       ::google::protobuf::Closure* done) {
            brpc::ClosureGuard rpc_guard(done);
            std::cout << "收到消息:" << request->message() << std::endl;

            std::string str = request->message() + "--这是响应！！";
            response->set_message(str);
            //done->Run();
        }
};
int main()
{

    logging::LoggingSettings settings;
    settings.logging_dest=logging::LoggingDestination::LOG_TO_NONE;
    logging::InitLogging(settings);
    brpc::Server server;
    EchoServiceImpl echo_service;
    int ret=server.AddService(&echo_service,brpc::ServiceOwnership::SERVER_DOESNT_OWN_SERVICE);
    if(ret==-1)
    {
        LOG_ERROR("添加rpc服务失败\n");
        return -1;
    }
    brpc::ServerOptions opts;
    opts.idle_timeout_sec=-1;//超时关闭时间
    opts.num_threads=1;
    ret=server.Start(8080,&opts);
    if(ret==-1)
    {
        LOG_ERROR("启动服务器失败\n");
        return -1;
    }
    server.RunUntilAskedToQuit();
}