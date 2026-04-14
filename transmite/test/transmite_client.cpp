#include "etcd.hpp"
#include "brpc.hpp"
#include "utils.hpp"
#include <gflags/gflags.h>
#include <gtest/gtest.h>
#include <thread>
#include "transmite.pb.h"


DEFINE_bool(run_mode, false, "程序的运行模式，false-调试； true-发布；");
DEFINE_string(log_file, "", "发布模式下，用于指定日志的输出文件");
DEFINE_int32(log_level, 0, "发布模式下，用于指定日志输出等级");

DEFINE_string(etcd_host, "http://127.0.0.1:2379", "服务注册中心地址");
DEFINE_string(base_service, "/service", "服务监控根目录");
DEFINE_string(transmite_service, "/service/transmite_service", "服务监控根目录");

luna::ServiceManager::ptr sm;

void string_message(const std::string &uid, const std::string &sid, const std::string &msg) {
    auto channel = sm->choose(FLAGS_transmite_service);
    if (!channel) {
        std::cout << "获取通信信道失败！" << std::endl;
        return;
    }
    luna::MsgTransmitService_Stub stub(channel.get());
    luna::NewMessageReq req;
    luna::GetTransmitTargetRsp rsp;
    req.set_request_id(luna::uuid());
    req.set_user_id(uid);
    req.set_chat_session_id(sid);
    req.mutable_message()->set_message_type(luna::MessageType::STRING);
    req.mutable_message()->mutable_string_message()->set_content(msg);
    brpc::Controller cntl;
    stub.GetTransmitTarget(&cntl, &req, &rsp, nullptr);
    ASSERT_FALSE(cntl.Failed());
    ASSERT_TRUE(rsp.success());
}
void image_message(const std::string &uid, const std::string &sid, const std::string &msg) {
    auto channel = sm->choose(FLAGS_transmite_service);
    if (!channel) {
        std::cout << "获取通信信道失败！" << std::endl;
        return;
    }
    luna::MsgTransmitService_Stub stub(channel.get());
    luna::NewMessageReq req;
    luna::GetTransmitTargetRsp rsp;
    req.set_request_id(luna::uuid());
    req.set_user_id(uid);
    req.set_chat_session_id(sid);
    req.mutable_message()->set_message_type(luna::MessageType::IMAGE);
    req.mutable_message()->mutable_image_message()->set_image_content(msg);
    brpc::Controller cntl;
    stub.GetTransmitTarget(&cntl, &req, &rsp, nullptr);
    ASSERT_FALSE(cntl.Failed());
    ASSERT_TRUE(rsp.success());
}

void speech_message(const std::string &uid, const std::string &sid, const std::string &msg) {
    auto channel = sm->choose(FLAGS_transmite_service);
    if (!channel) {
        std::cout << "获取通信信道失败！" << std::endl;
        return;
    }
    luna::MsgTransmitService_Stub stub(channel.get());
    luna::NewMessageReq req;
    luna::GetTransmitTargetRsp rsp;
    req.set_request_id(luna::uuid());
    req.set_user_id(uid);
    req.set_chat_session_id(sid);
    req.mutable_message()->set_message_type(luna::MessageType::SPEECH);
    req.mutable_message()->mutable_speech_message()->set_file_contents(msg);
    brpc::Controller cntl;
    stub.GetTransmitTarget(&cntl, &req, &rsp, nullptr);
    ASSERT_FALSE(cntl.Failed());
    ASSERT_TRUE(rsp.success());
}

void file_message(const std::string &uid, const std::string &sid, 
    const std::string &filename, const std::string &content) {
    auto channel = sm->choose(FLAGS_transmite_service);
    if (!channel) {
        std::cout << "获取通信信道失败！" << std::endl;
        return;
    }
    luna::MsgTransmitService_Stub stub(channel.get());
    luna::NewMessageReq req;
    luna::GetTransmitTargetRsp rsp;
    req.set_request_id(luna::uuid());
    req.set_user_id(uid);
    req.set_chat_session_id(sid);
    req.mutable_message()->set_message_type(luna::MessageType::FILE);
    req.mutable_message()->mutable_file_message()->set_file_contents(content);
    req.mutable_message()->mutable_file_message()->set_file_name(filename);
    req.mutable_message()->mutable_file_message()->set_file_size(content.size());
    brpc::Controller cntl;
    stub.GetTransmitTarget(&cntl, &req, &rsp, nullptr);
    ASSERT_FALSE(cntl.Failed());
    ASSERT_TRUE(rsp.success());
}

int main(int argc, char *argv[])
{
    google::ParseCommandLineFlags(&argc, &argv, true);
    init_logger(FLAGS_run_mode, FLAGS_log_file, FLAGS_log_level);

    
    //1. 先构造Rpc信道管理对象
    sm = std::make_shared<luna::ServiceManager>();
    sm->declared(FLAGS_transmite_service);
    auto put_cb = std::bind(&luna::ServiceManager::onServiceOnline, sm.get(), std::placeholders::_1, std::placeholders::_2);
    auto del_cb = std::bind(&luna::ServiceManager::onServiceOffline, sm.get(), std::placeholders::_1, std::placeholders::_2);
    //2. 构造服务发现对象
    luna::Discovery::ptr dclient = std::make_shared<luna::Discovery>(FLAGS_etcd_host, FLAGS_base_service, put_cb, del_cb);
    
    //3. 通过Rpc信道管理对象，获取提供Echo服务的信道
     string_message("6220-a39de735-0000", "会话ID1", "吃饭了吗？");
     string_message("67e0-e57f5e21-0001", "会话ID1", "吃的盖浇饭！！");
     image_message("67e0-e57f5e21-0001", "会话ID1", "可爱表情图片数据");
     speech_message("67e0-e57f5e21-0001", "会话ID1", "动听猪叫声数据");
     file_message("67e0-e57f5e21-0001", "会话ID1", "猪爸爸的文件名称", "猪爸爸的文件数据");
     LOG_DEBUG("message update done");
//     auto channel = sm->choose(FLAGS_transmite_service);
//     if (!channel) {
//         std::cout << "获取通信信道失败！" << std::endl;
//         return -1;
//     }
//     luna::MsgTransmitService_Stub stub(channel.get());
//     luna::NewMessageReq req;
//     luna::GetTransmitTargetRsp rsp;
//     req.set_request_id(luna::uuid());
//     req.set_user_id("6220-a39de735-0000");
//     req.set_chat_session_id("会话ID1");
//     req.mutable_message()->set_message_type(luna::MessageType::STRING);
//     req.mutable_message()->mutable_file_message()->set_file_contents("测试消息");
//     brpc::Controller cntl;
//     stub.GetTransmitTarget(&cntl, &req, &rsp, nullptr);
//     if(cntl.Failed()==true)
//     {
//         cout<<rsp.errmsg()<<endl;
//         return -1;
//     }
//     if(rsp.success()==false)
//     {
//         cout<<rsp.errmsg()<<endl;
//         return -1;
//     }
//     /*/这个用于内部的通信,生成完整的消息信息，并获取消息的转发人员列表
//     message GetTransmitTargetRsp {
//     string request_id = 1;
//     bool success = 2;
//     string errmsg = 3; 
//     MessageInfo message = 4; // 组织好的消息结构 -- 
//     repeated string target_id_list = 5; //消息的转发目标列表
//     //消息结构
//     message MessageInfo {
//     string message_id = 1;//消息ID
//     string chat_session_id = 2;//消息所属聊天会话ID
//     int64 timestamp = 3;//消息产生时间
//     UserInfo sender = 4;//消息发送者信息
//     MessageContent message = 5;
// }
// }*/
//     cout<<"rsp id "<<rsp.request_id()<<endl;
//     cout<<"success"<<rsp.success()<<endl;
//     cout<<"error msg"<<rsp.errmsg()<<endl;
//     cout<<"chat_session_id"<<rsp.message().chat_session_id()<<endl;
//     cout<<"timestamp"<<rsp.message().timestamp()<<endl;
//     cout<<"sender"<<rsp.message().sender().nickname()<<endl;
//     for(int i=0;i<rsp.target_id_list_size();i++)
//     {
//         cout<<" target "<<rsp.target_id_list(i)<<endl;
//     }
//     return 0;
}