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

namespace luna {

// ============================================================================
// SessionMemberCache — 群成员列表的 Redis 缓存层
// ============================================================================
// 特性:
//   - Cache-Aside 模式: 读缓存 → miss → db_loader 回源 → 回填
//   - 防穿透: 空结果写入哨兵值 (短 TTL)
//   - 防击穿: 分片互斥锁, 同一 key 只有一个线程回源 MySQL
//   - 防雪崩: TTL + 随机抖动
//   - 主动失效: invalidate() → DEL cache_key
//
// 用法:
//   auto table = std::make_shared<ChatSessionMemberTable>(mysql);
//   auto loader = [table](const std::string& ssid) { return table->members(ssid); };
//   auto cache = std::make_shared<SessionMemberCache>(redis, loader);
//   auto members = cache->get("group_123");
// ============================================================================

class SessionMemberCache {
public:
    using ptr = std::shared_ptr<SessionMemberCache>;

    // 回源查询回调: chat_ssid → uid 列表
    using DbLoader = std::function<std::vector<std::string>(const std::string& chat_ssid)>;

    SessionMemberCache(std::shared_ptr<sw::redis::Redis> redis, DbLoader db_loader)
        : _redis(std::move(redis)), _db_loader(std::move(db_loader)) {}

    // ------------------------------------------------------------------
    // 获取成员列表 (缓存优先, miss 时回源)
    // ------------------------------------------------------------------
    std::vector<std::string> get(const std::string& chat_ssid) {
        std::string key = cache_key(chat_ssid);

        // 1. 查 Redis
        auto cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            if (*cached == EMPTY_SENTINEL) return {};
            return split(*cached);
        }

        // 2. Miss — 获取分片锁 (防击穿)
        size_t shard = std::hash<std::string>{}(key) % MUTEX_SHARDS;
        std::lock_guard<std::mutex> lock(_mutexes[shard]);

        // 3. Double-check (等锁期间可能已被其他线程填充)
        cached = _redis->get(key);
        if (cached) {
            _hits.fetch_add(1, std::memory_order_relaxed);
            if (*cached == EMPTY_SENTINEL) return {};
            return split(*cached);
        }

        // 4. 回源 DB
        _misses.fetch_add(1, std::memory_order_relaxed);
        auto members = _db_loader(chat_ssid);

        // 5. 回填 Redis (TTL + 随机抖动, 防雪崩)
        int ttl = members.empty()
            ? TTL_EMPTY                                     // 空结果短 TTL (防穿透)
            : TTL_BASE + jitter();                           // 正常 TTL + 抖动
        std::string value = members.empty() ? EMPTY_SENTINEL : join(members);
        _redis->set(key, value, std::chrono::seconds(ttl));

        return members;
    }

    // ------------------------------------------------------------------
    // 主动失效: 成员变更时调用
    // ------------------------------------------------------------------
    void invalidate(const std::string& chat_ssid) {
        _redis->del(cache_key(chat_ssid));
    }

    // ------------------------------------------------------------------
    // 统计信息
    // ------------------------------------------------------------------
    struct Stats {
        long hits;
        long misses;
    };

    Stats stats() const {
        return { _hits.load(std::memory_order_relaxed),
                 _misses.load(std::memory_order_relaxed) };
    }

private:
    static constexpr int TTL_BASE   = 5;   // 正常缓存秒数
    static constexpr int TTL_EMPTY  = 2;   // 空哨兵秒数 (防穿透)
    static constexpr int TTL_JITTER = 2;   // 随机抖动上限秒数 (防雪崩)
    static constexpr int MUTEX_SHARDS = 64; // 互斥锁分片数
    static constexpr const char* KEY_PREFIX = "session_members:";
    static constexpr const char* EMPTY_SENTINEL = "__EMPTY__";

    std::string cache_key(const std::string& chat_ssid) const {
        return KEY_PREFIX + chat_ssid;
    }

    // 线程安全的 TTL 随机抖动
    static int jitter() {
        thread_local std::mt19937 gen(std::random_device{}());
        thread_local std::uniform_int_distribution<int> dist(0, TTL_JITTER);
        return dist(gen);
    }

    // CSV 序列化
    static std::string join(const std::vector<std::string>& v) {
        if (v.empty()) return "";
        std::ostringstream oss;
        for (size_t i = 0; i < v.size(); ++i) {
            if (i) oss << ',';
            oss << v[i];
        }
        return oss.str();
    }

    // CSV 反序列化
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
};

} // namespace luna
