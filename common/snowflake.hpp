#pragma once
#include <cstdint>
#include <chrono>
#include <mutex>

class Snowflake {
public:
    Snowflake(uint16_t machine_id)
        : machine_id_(machine_id & 0x3FF) // 10bit
    {}

    uint64_t next_id() {
        std::lock_guard<std::mutex> lock(mtx_);

        uint64_t now = time_now();

        if (now == last_time_) {
            seq_ = (seq_ + 1) & 0xFFF; // 12bit

            if (seq_ == 0) {
                while ((now = time_now()) <= last_time_);
            }
        } else {
            seq_ = 0;
        }

        last_time_ = now;

        return ((now - epoch_) << 22)
             | (machine_id_ << 12)
             | seq_;
    }

private:
    uint64_t time_now() {
        using namespace std::chrono;
        return duration_cast<milliseconds>(
            system_clock::now().time_since_epoch()
        ).count();
    }

private:
    const uint64_t epoch_ = 1700000000000ULL; // 起始时间

    uint64_t last_time_ = 0;
    uint16_t machine_id_;
    uint16_t seq_ = 0;

    std::mutex mtx_;
};