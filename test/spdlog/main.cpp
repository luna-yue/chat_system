#include "logger.hpp"
#include <gflags/gflags.h>
DEFINE_bool(run_mode,false,"程序的运行模式 false调试 true 发布");
DEFINE_string(log_file,"","发布模式下用于指定日志的输出文件");
DEFINE_int32(log_level,0,"发布模式下指定日志输出等级");
int main(int argc ,char *argv[])
{
    google::ParseCommandLineFlags(&argc,&argv,true);
    std::cout<<FLAGS_run_mode<<FLAGS_log_file<<FLAGS_log_level<<std::endl;
    init_logger(FLAGS_run_mode,FLAGS_log_file,FLAGS_log_level);
    LOG_DEBUG("hello sb");
    LOG_INFO("hello sb");
    LOG_WARN("hello sb");
    LOG_ERROR("hello sb");
    LOG_FATAL("hello sb");
    //LOG_DEBUG("hello sb");
    //LOG_DEBUG("hello sb");
  
}