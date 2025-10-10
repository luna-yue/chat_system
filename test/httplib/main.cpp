#include "../../common/httplib.h"
void callback(const httplib::Request &req,httplib::Response &rsp)
{
    std::string s="<h1>"+req.method+"hello"+"</h1>";
    rsp.set_content(s,"text/html");
    rsp.status=200;
    
}
int main()
{
    httplib::Server tmp;
    tmp.Get("/hi",callback);
    tmp.listen("0.0.0.0",8512);
}