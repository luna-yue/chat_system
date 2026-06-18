#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>

#include "httplib.h"

#include "base.pb.h"
#include "user.pb.h"

std::atomic<int> success_cnt(0);
std::atomic<int> failed_cnt(0);

const std::string HOST = "49.232.249.2";
const int PORT = 9000;

void worker(int begin_idx, int end_idx)
{
    // 每个线程一个Client
    httplib::Client cli(HOST, PORT);

    cli.set_connection_timeout(30, 0);
cli.set_read_timeout(30, 0);
cli.set_write_timeout(30, 0);

    for(int i = begin_idx; i <= end_idx; ++i)
    {
        luna::UserLoginReq req;

        req.set_request_id(std::to_string(i));

        char nickname[32];
        snprintf(
            nickname,
            sizeof(nickname),
            "user%05d",
            i);

        req.set_nickname(nickname);
        req.set_password("123456");

        std::string body;

        if(!req.SerializeToString(&body))
        {
            failed_cnt++;
            continue;
        }

        auto rsp = cli.Post(
            "/service/user/username_login",
            body,
            "application/x-protobuf");

        if(!rsp)
        {
            failed_cnt++;
            auto err = rsp.error();

    std::cout
<< "req=" << i
<< " err=" << (int)err
<< " socket_open="
<< cli.is_socket_open()
<< std::endl;
        continue;
        }

        if(rsp->status != 200)
        {
            failed_cnt++;
            continue;
        }

        luna::UserLoginRsp login_rsp;

        if(!login_rsp.ParseFromString(rsp->body))
        {
            failed_cnt++;
            continue;
        }

        if(login_rsp.success())
        {
            success_cnt++;
        }
        else
        {
            failed_cnt++;
        }
    }
}

int main(int argc, char* argv[])
{
    if(argc != 3)
    {
        std::cout
            << "Usage: "
            << argv[0]
            << " thread_num total_requests\n";

        return -1;
    }

    int thread_num = std::stoi(argv[1]);
    int total_requests = std::stoi(argv[2]);

    std::vector<std::thread> threads;

    int per_thread =
        total_requests / thread_num;

    auto begin =
        std::chrono::steady_clock::now();

    for(int t = 0; t < thread_num; ++t)
    {
        int start =
            t * per_thread + 1;

        int end =
            (t == thread_num - 1)
            ? total_requests
            : start + per_thread - 1;

        threads.emplace_back(
            worker,
            start,
            end);
    }

    for(auto& th : threads)
    {
        th.join();
    }

    auto finish =
        std::chrono::steady_clock::now();

    double seconds =
        std::chrono::duration<double>(
            finish - begin).count();

    std::cout << "\n========== RESULT ==========\n";

    std::cout
        << "Threads : "
        << thread_num
        << std::endl;

    std::cout
        << "Requests: "
        << total_requests
        << std::endl;

    std::cout
        << "Success : "
        << success_cnt.load()
        << std::endl;

    std::cout
        << "Failed  : "
        << failed_cnt.load()
        << std::endl;

    std::cout
        << "Time(s) : "
        << seconds
        << std::endl;

    std::cout
        << "QPS     : "
        << success_cnt.load() / seconds
        << std::endl;

    return 0;
}