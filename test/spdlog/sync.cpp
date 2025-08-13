#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <iostream>
int main()
{
    //全局 每秒刷新
    spdlog::flush_every(std::chrono::seconds(1));
    //遇到debug以上等级日志立即刷新
    spdlog::flush_on(spdlog::level::level_enum::debug);
    //全局日志输出等级 除此之外每个日志可以单独设置
    spdlog::set_level(spdlog::level::level_enum::debug);
     auto logger=spdlog::basic_logger_mt("file-logger","test_origin.log");
     logger->set_pattern("[%n][%H:%M:%S][%t][%-8l] %v");
     logger->trace("hello ?");
     logger->debug("hello {} sb");
     logger->info("hello {} sb");
     logger->warn("hello {} sb");
     logger->error("hello {} sb");
     logger->critical("hello {} sb");
}