#pragma once
#include <sw/redis++/redis++.h>
#include <functional>
#include <optional>
#include <string>
#include <mutex>
#include <array>
#include <atomic>
#include <random>
#include <chrono>
#include <unordered_map>

#include "base.pb.h"

namespace luna {

// ============================================================================
// UserInfoCache — 三级缓存: 本地 → Redis → User RPC
// ============================================================================
// L1: 进程内 unordered_map          ~0.2us
// L2: Redis                         ~150us
// L3: User 服务 RPC (DbLoader)      ~900us
// ============================================================================

class UserInfoCache {
public:
    using ptr = std::shared_ptr<UserInfoCache>;
    using DbLoader = std::function<std::optional<luna::UserInfo>(const std::string& user_id)>;

    UserInfoCache(std::shared_ptr<sw::redis::Redis> redis, DbLoader db_loader)
        : _redis(std::move(redis)), _db_loader(std::move(db_loader)) {}

    // ------------------------------------------------------------------
    // 获取用户信息 (L1 → L2 → L3)
    // ------------------------------------------------------------------
    std::optional<luna::UserInfo> get(const std::string& user_id) {
        // ── L1: 本地缓存 ──
        {
            auto it = _local.find(user_id);
            if (it != _local.end()) {
                auto elapsed = std::chrono::steady_clock::now() - it->second.since;
                if (elapsed < std::chrono::seconds(L1_TTL)) {
                    _hits.fetch_add(1, std::memory_order_relaxed);
                    luna::UserInfo info;
                    if (info.ParseFromString(it->second.value))
                        return info;
                }
                _local.erase(it);
            }
        }

        std::string key = cache_key(user_id);

        // ── L2: Redis ──
        auto cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            _local_set(user_id, *cached);
            luna::UserInfo info;
            if (info.ParseFromString(*cached))
                return info;
        }

        // Miss — 分片锁 (防击穿)
        size_t shard = std::hash<std::string>{}(key) % MUTEX_SHARDS;
        std::lock_guard<std::mutex> lock(_mutexes[shard]);

        // Double-check
        cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            _local_set(user_id, *cached);
            luna::UserInfo info;
            if (info.ParseFromString(*cached))
                return info;
        }

        // ── L3: User RPC ──
        _misses.fetch_add(1, std::memory_order_relaxed);
        auto info = _db_loader(user_id);
        if (!info.has_value()) return std::nullopt;

        std::string serialized;
        if (info->SerializeToString(&serialized)) {
            int ttl = TTL_BASE + jitter();
            _redis->set(key, serialized, std::chrono::seconds(ttl));
            _local_set(user_id, serialized);
        }
        return info;
    }

    // ------------------------------------------------------------------
    // 主动失效: 清 L2 + L1
    // ------------------------------------------------------------------
    void invalidate(const std::string& user_id) {
        _redis->del(cache_key(user_id));
        _local.erase(user_id);
    }

    struct Stats { long hits; long misses; };
    Stats stats() const {
        return { _hits.load(std::memory_order_relaxed),
                 _misses.load(std::memory_order_relaxed) };
    }

private:
    static constexpr int TTL_BASE   = 60;
    static constexpr int TTL_JITTER = 10;
    static constexpr int L1_TTL     = 10;  // L1 比 L2 短, 快速感知失效
    static constexpr int MUTEX_SHARDS = 64;
    static constexpr const char* KEY_PREFIX = "user_info:";

    struct LocalEntry {
        std::string value;
        std::chrono::steady_clock::time_point since;
    };

    static std::string cache_key(const std::string& uid) { return KEY_PREFIX + uid; }

    void _local_set(const std::string& uid, const std::string& value) {
        _local[uid] = {value, std::chrono::steady_clock::now()};
    }

    static int jitter() {
        thread_local std::mt19937 gen(std::random_device{}());
        thread_local std::uniform_int_distribution<int> dist(0, TTL_JITTER);
        return dist(gen);
    }

    std::shared_ptr<sw::redis::Redis> _redis;
    DbLoader _db_loader;
    std::array<std::mutex, MUTEX_SHARDS> _mutexes;
    std::atomic<long> _hits{0};
    std::atomic<long> _misses{0};
    std::unordered_map<std::string, LocalEntry> _local;
};

} // namespace luna
