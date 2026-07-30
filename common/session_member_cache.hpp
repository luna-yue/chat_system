#pragma once
#include <sw/redis++/redis++.h>
#include <functional>
#include <vector>
#include <string>
#include <mutex>
#include <array>
#include <atomic>
#include <random>
#include <sstream>
#include <chrono>
#include <unordered_map>

namespace luna {

// ============================================================================
// SessionMemberCache — 三级缓存: 本地 → Redis → MySQL
// ============================================================================
// L1: 进程内 unordered_map         ~0.2us (无网络, 无序列化)
// L2: Redis                         ~150us
// L3: MySQL (db_loader 回调)        ~5000us
//
// 多进程部署时各进程 L1 独立, 无并发冲突.
// 一致性: L2 被 Friend 主动失效后, L1 靠短 TTL 自然过期.
// ============================================================================

class SessionMemberCache {
public:
    using ptr = std::shared_ptr<SessionMemberCache>;
    using DbLoader = std::function<std::vector<std::string>(const std::string& chat_ssid)>;

    SessionMemberCache(std::shared_ptr<sw::redis::Redis> redis, DbLoader db_loader)
        : _redis(std::move(redis)), _db_loader(std::move(db_loader)) {}

    // ------------------------------------------------------------------
    // 获取成员列表 (L1 → L2 → L3)
    // ------------------------------------------------------------------
    std::vector<std::string> get(const std::string& chat_ssid) {
        // ── L1: 本地缓存 ──
        {
            auto it = _local.find(chat_ssid);
            if (it != _local.end()) {
                auto elapsed = std::chrono::steady_clock::now() - it->second.since;
                if (elapsed < std::chrono::seconds(L1_TTL)) {
                    _hits.fetch_add(1, std::memory_order_relaxed);
                    if (it->second.value == EMPTY_SENTINEL) return {};
                    return split(it->second.value);
                }
                // 过期了, 删掉, 往下走
                _local.erase(it);
            }
        }

        std::string key = cache_key(chat_ssid);

        // ── L2: Redis ──
        auto cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            _local_set(chat_ssid, *cached);
            if (*cached == EMPTY_SENTINEL) return {};
            return split(*cached);
        }

        // Miss — 分片锁 (防击穿)
        size_t shard = std::hash<std::string>{}(key) % MUTEX_SHARDS;
        std::lock_guard<std::mutex> lock(_mutexes[shard]);

        // Double-check
        cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            _local_set(chat_ssid, *cached);
            if (*cached == EMPTY_SENTINEL) return {};
            return split(*cached);
        }

        // ── L3: MySQL ──
        _misses.fetch_add(1, std::memory_order_relaxed);
        auto members = _db_loader(chat_ssid);

        // 回填 L2 + L1
        int ttl = members.empty() ? TTL_EMPTY : TTL_BASE + jitter();
        std::string value = members.empty() ? EMPTY_SENTINEL : join(members);
        _redis->set(key, value, std::chrono::seconds(ttl));
        _local_set(chat_ssid, value);

        return members;
    }

    // ------------------------------------------------------------------
    // 主动失效: 清 L2, L1 靠短 TTL 自然过期
    // ------------------------------------------------------------------
    void invalidate(const std::string& chat_ssid) {
        _redis->del(cache_key(chat_ssid));
        _local.erase(chat_ssid);
    }

    struct Stats {
        long hits;
        long misses;
    };
    Stats stats() const {
        return { _hits.load(std::memory_order_relaxed),
                 _misses.load(std::memory_order_relaxed) };
    }

private:
    static constexpr int TTL_BASE   = 5;
    static constexpr int TTL_EMPTY  = 2;
    static constexpr int TTL_JITTER = 2;
    static constexpr int L1_TTL     = 2;  // L1 过期比 L2 短, 快速感知失效
    static constexpr int MUTEX_SHARDS = 64;
    static constexpr const char* KEY_PREFIX = "session_members:";
    static constexpr const char* EMPTY_SENTINEL = "__EMPTY__";

    struct LocalEntry {
        std::string value;
        std::chrono::steady_clock::time_point since;
    };

    std::string cache_key(const std::string& s) const { return KEY_PREFIX + s; }

    void _local_set(const std::string& chat_ssid, const std::string& value) {
        _local[chat_ssid] = {value, std::chrono::steady_clock::now()};
    }

    static int jitter() {
        thread_local std::mt19937 gen(std::random_device{}());
        thread_local std::uniform_int_distribution<int> dist(0, TTL_JITTER);
        return dist(gen);
    }

    static std::string join(const std::vector<std::string>& v) {
        if (v.empty()) return "";
        std::ostringstream oss;
        for (size_t i = 0; i < v.size(); ++i) {
            if (i) oss << ',';
            oss << v[i];
        }
        return oss.str();
    }
    static std::vector<std::string> split(const std::string& s) {
        std::vector<std::string> res;
        size_t start = 0, end;
        while ((end = s.find(',', start)) != std::string::npos) {
            res.push_back(s.substr(start, end - start));
            start = end + 1;
        }
        if (start < s.size()) res.push_back(s.substr(start));
        return res;
    }

    std::shared_ptr<sw::redis::Redis> _redis;
    DbLoader _db_loader;
    std::array<std::mutex, MUTEX_SHARDS> _mutexes;
    std::atomic<long> _hits{0};
    std::atomic<long> _misses{0};

    // L1 本地缓存: 单进程内无并发竞争 (Transmite 单进程)
    std::unordered_map<std::string, LocalEntry> _local;
};

} // namespace luna
