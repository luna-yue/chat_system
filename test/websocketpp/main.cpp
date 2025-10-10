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