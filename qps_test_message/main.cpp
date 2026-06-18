#include "httplib.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>
#include <unordered_map>

#include "base.pb.h"
#include "user.pb.h"
#include "message.pb.h"
#include "transmite.pb.h"

const std::string HOST = "127.0.0.1";
const int PORT = 9000;

std::atomic<int> success_cnt(0);
std::atomic<int> failed_cnt(0);

std::unordered_map<
    std::string,
    std::string> g_sessions;

bool login_user(
    const std::string& nickname,
    const std::string& password)
{
    httplib::Client cli(HOST, PORT);

    luna::UserLoginReq req;

    req.set_request_id(nickname);
    req.set_nickname(nickname);
    req.set_password(password);

    std::string body;

    if(!req.SerializeToString(&body))
        return false;

    auto rsp =
        cli.Post(
            "/service/user/username_login",
            body,
            "application/x-protobuf");

    if(!rsp)
        return false;

    luna::UserLoginRsp login_rsp;

    if(!login_rsp.ParseFromString(
            rsp->body))
        return false;

    if(!login_rsp.success())
        return false;

    g_sessions[nickname] =
        login_rsp.login_session_id();

    return true;
}

bool login_all_users()
{
    for(int i = 1; i <= 100; i++)
    {
        char nickname[32];

        snprintf(
            nickname,
            sizeof(nickname),
            "user%05d",
            i);

        bool ret =
            login_user(
                nickname,
                "123456");

        if(!ret)
        {
            std::cout
                << "login failed: "
                << nickname
                << std::endl;

            return false;
        }
    }

    return true;
}

void worker(
    int begin_idx,
    int end_idx)
{
    httplib::Client cli(
        HOST,
        PORT);

    cli.set_connection_timeout(30);
    cli.set_read_timeout(30);

    for(int i = begin_idx;
        i <= end_idx;
        ++i)
    {
        int uid =
            rand() % 100 + 1;

        char nickname[32];

        snprintf(
            nickname,
            sizeof(nickname),
            "user%05d",
            uid);

        auto it =
            g_sessions.find(
                nickname);

        if(it ==
           g_sessions.end())
        {
            failed_cnt++;
            continue;
        }

        luna::NewMessageReq req;

        req.set_request_id(
            std::to_string(i));

        req.set_session_id(
            it->second);

        req.set_chat_session_id(
            "stress_group_100");

        auto* msg =
            req.mutable_message();

        msg->set_message_type(
            luna::MessageType::STRING);

        msg->mutable_string_message()
            ->set_content(
                "pressure test");

        std::string body;

        if(!req.SerializeToString(
                &body))
        {
            failed_cnt++;
            continue;
        }

        auto rsp =
            cli.Post(
                "/service/message_transmit/new_message",
                body,
                "application/x-protobuf");

        if(!rsp)
        {
            failed_cnt++;

            std::cout
                << "http error="
                << (int)rsp.error()
                << std::endl;

            continue;
        }

        if(rsp->status != 200)
        {
            failed_cnt++;
            continue;
        }

        luna::NewMessageRsp msg_rsp;

        if(!msg_rsp.ParseFromString(
                rsp->body))
        {
            failed_cnt++;
            continue;
        }

        if(msg_rsp.success())
        {
            success_cnt++;
        }
        else
        {
            failed_cnt++;
        }
    }
}

void run_test(
    int thread_num,
    int total_requests)
{
    std::vector<std::thread> threads;

    int per_thread =
        total_requests /
        thread_num;

    auto begin =
        std::chrono::
            steady_clock::now();

    for(int t = 0;
        t < thread_num;
        ++t)
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
        std::chrono::
            steady_clock::now();

    double seconds =
        std::chrono::
        duration_cast<
            std::chrono::milliseconds>(
                finish - begin)
            .count()
        / 1000.0;

    std::cout
        << "\n========== RESULT ==========\n";

    std::cout
        << "Threads : "
        << thread_num
        << "\n";

    std::cout
        << "Requests: "
        << total_requests
        << "\n";

    std::cout
        << "Success : "
        << success_cnt
        << "\n";

    std::cout
        << "Failed  : "
        << failed_cnt
        << "\n";

    std::cout
        << "Time(s) : "
        << seconds
        << "\n";

    std::cout
        << "QPS     : "
        << total_requests / seconds
        << "\n";
}

int main(
    int argc,
    char* argv[])
{
    int thread_num = 20;
    int total_requests = 10000;

    if(argc >= 3)
    {
        thread_num =
            atoi(argv[1]);

        total_requests =
            atoi(argv[2]);
    }

    if(!login_all_users())
    {
        std::cout
            << "login users failed"
            << std::endl;

        return -1;
    }

    run_test(
        thread_num,
        total_requests);

    return 0;
}