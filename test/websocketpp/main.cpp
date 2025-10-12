#include <iostream>
#include <websocketpp/config/asio_no_tls.hpp>
#include <websocketpp/server.hpp>

using namespace std;

typedef websocketpp::server<websocketpp::config::asio>
    websocketsvr;
typedef websocketsvr::message_ptr message_ptr;
using websocketpp::lib::bind;
using websocketpp::lib::placeholders::_1;
using websocketpp::lib::placeholders::_2;

void OnOpen(websocketsvr *server, websocketpp::connection_hdl hdl)
{
    cout << "success connect" << '\n';
}
void OnClose(websocketsvr *server, websocketpp::connection_hdl hdl)
{
    cout << "connection close" << '\n';
}
void OnMessage(websocketsvr *server,
               websocketpp::connection_hdl hdl,
               message_ptr msg)
{
    cout<<"message received "<<msg->get_payload()<<'\n';
    server->send(hdl,msg->get_payload(),websocketpp::frame::opcode::text);
}
void OnFail(websocketsvr *server, websocketpp::connection_hdl hdl)
{
    cout<<"connection error"<<'\n';
}
void OnHttp(websocketsvr *server, websocketpp::connection_hdl hdl)
{
    cout<<"处理http请求"<<'\n';
    websocketsvr::connection_ptr con=server->get_con_from_hdl(hdl);
    std::stringstream ss;
    ss<< "<!doctype html><html><head>" 
        << "<title>hello websocket</title><body>" 
        << "<h1>hello websocketpp</h1>" 
        << "</body></head></html>"; 
    con->set_body(ss.str());
    con->set_status(websocketpp::http::status_code::ok);
}
int main(){
    //websocket 全双工通信，允许客户端和服务器实时双向通信
    //建立http连接后使用http/1.1 Connection: Upgrade 进行升级 
    //Sec-WebSocket-Key 是客户端生成的随机字符串
    //，用于在握手阶段让服务器生成唯一响应，从而防止中间人或非 WebSocket 请求伪造连接。
    //tls协议， 协商tls版本 加密方式 随机数， 随后服务端发送证书（含服务器公钥）
    //客户端生成预主密钥 并用服务器公钥（那么只有服务器能用私钥解密）加密发给 服务端
    //双方用两端生成的随机数和预主密钥生成会话密钥。
    //整个过程中真正的会话密钥不在网络传输 而是双方独自生成 依赖于证书的可靠性
    //证书包含域名 公钥 签名 ，如果用ca公钥哈希证书信息得到的与签名匹配可信
    //如果域名或公钥被修改 则ca公钥哈希后与签名不同 
    //wss =websocket + tls
    
    websocketsvr server;
    server.set_access_channels(websocketpp::log::alevel::none);
    server.init_asio();
    server.set_http_handler(bind(&OnHttp,&server,::_1));
    server.set_close_handler(bind(&OnClose,&server,_1));
    server.set_message_handler(bind(&OnMessage,&server,_1,_2));
    server.listen(8888);
    server.start_accept();
    server.run();
    return 0;
}