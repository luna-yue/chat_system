#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/async.h>
#include <iostream>
int main()
{
    spdlog::flush_every(std::chrono::seconds(1));
    spdlog::flush_on(spdlog::level::level_enum::debug);
    spdlog::set_level(spdlog::level::level_enum::debug);
    spdlog::init_thread_pool(3072,1);
    auto logger=spdlog::stdout_color_mt<spdlog::async_factory>("async-logger");
    logger->set_pattern("[%n][%H:%M:%S][%t][%-8l] %v");
    logger->trace("hello sb");
    logger->debug("hello sb");
    logger->info("hello sb");
    logger->warn("hello sb");
    logger->error("hello sb");
    logger->critical("hello sb");
}