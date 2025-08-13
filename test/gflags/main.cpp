#include <gflags/gflags.h>
#include <iostream>
using namespace std;
DEFINE_string(ip,"127.0.0.1","Server ip 格式127.0.0.1");
DEFINE_int32(port,8080,"Server port 格式:8080");
DEFINE_bool(if_debug,true,"是否启用调试模式 格式 true/false");
int main(int argc ,char * argv[])
{
    gflags::ParseCommandLineFlags(&argc,&argv,true);
    if(FLAGS_if_debug)
    cout<<FLAGS_ip<<" "<<FLAGS_port<<endl;
}