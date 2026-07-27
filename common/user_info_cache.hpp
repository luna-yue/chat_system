#pragma once
#include <sw/redis++/redis++.h>
#include <functional>
#include <optional>
#include <string>
#include <mutex>
#include <array>
#include <atomic>
#include <random>

#include "base.pb.h"

namespace luna {

// ============================================================================
// UserInfoCache — 用户信息缓存, 消除 Transmite → User 的嵌套 RPC
// ============================================================================
// 与 SessionMemberCache 同样的设计模式:
//   - Cache-Aside: 查 Redis → miss → DbLoader(RPC) → 回填
//   - 防击穿: 64 分片互斥锁
//   - 防雪崩: TTL + 随机抖动
//   - 主动失效: invalidate() → DEL key
//
// 用法:
//   auto loader = [&](const std::string& uid) -> std::optional<UserInfo> {
//       // 调 User 服务 RPC
//   };
//   auto cache = std::make_shared<UserInfoCache>(redis, loader);
//   auto sender = cache->get(uid);
// ============================================================================

class UserInfoCache {
public:
    using ptr = std::shared_ptr<UserInfoCache>;

    // 回源查询: user_id → UserInfo (nullopt = 查询失败 / 用户不存在)
    using DbLoader = std::function<std::optional<luna::UserInfo>(const std::string& user_id)>;

    UserInfoCache(std::shared_ptr<sw::redis::Redis> redis, DbLoader db_loader)
        : _redis(std::move(redis)), _db_loader(std::move(db_loader)) {}

    // ------------------------------------------------------------------
    // 获取用户信息 (缓存优先)
    // ------------------------------------------------------------------
    std::optional<luna::UserInfo> get(const std::string& user_id) {
        std::string key = cache_key(user_id);

        // 1. 查 Redis
        auto cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            luna::UserInfo info;
            if (info.ParseFromString(*cached))
                return info;
            // 反序列化失败视为 miss, 走回源
        }

        // 2. Miss — 分片锁 (防击穿)
        size_t shard = std::hash<std::string>{}(key) % MUTEX_SHARDS;
        std::lock_guard<std::mutex> lock(_mutexes[shard]);

        // 3. Double-check
        cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            luna::UserInfo info;
            if (info.ParseFromString(*cached))
                return info;
        }

        // 4. 回源 (RPC 调用 User 服务)
        _misses.fetch_add(1, std::memory_order_relaxed);
        auto info = _db_loader(user_id);
        if (!info.has_value()) return std::nullopt;

        // 5. 回填 Redis
        std::string serialized;
        if (info->SerializeToString(&serialized)) {
            int ttl = TTL_BASE + jitter();
            _redis->set(key, serialized, std::chrono::seconds(ttl));
        }
        return info;
    }

    // ------------------------------------------------------------------
    // 主动失效: 用户信息变更时调用 (改昵称/头像等)
    // ------------------------------------------------------------------
    void invalidate(const std::string& user_id) {
        _redis->del(cache_key(user_id));
    }

    // ------------------------------------------------------------------
    // 统计
    // ------------------------------------------------------------------
    struct Stats { long hits; long misses; };
    Stats stats() const {
        return { _hits.load(std::memory_order_relaxed),
                 _misses.load(std::memory_order_relaxed) };
    }

private:
    // 用户信息变更频率低, TTL 设长一些
    static constexpr int TTL_BASE   = 60;  // 基础 1 分钟
    static constexpr int TTL_JITTER = 10;  // 抖动 0~10s
    static constexpr int MUTEX_SHARDS = 64;
    static constexpr const char* KEY_PREFIX = "user_info:";

    static std::string cache_key(const std::string& user_id) {
        return KEY_PREFIX + user_id;
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
};

} // namespace luna
