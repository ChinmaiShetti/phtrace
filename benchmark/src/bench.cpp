// Replays the workload traces (workload/gen.py) against one index and writes per-phase metrics.
//
//   bench --index btree|alex|alexhb|alexhb-nomig --traces DIR --rep N --out results.csv
//         [--hb-window W] [--hb-hot H] [--hb-migrate M]      (ALEX-HB parameters, see docs/experiment-phase4.md)
//
// Every operation is timed individually with steady_clock into a preallocated buffer; the trace is
// fully in memory before timing starts. One index per process, so runs do not share heap state.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "alex.h"
#include <tlx/container/btree_map.hpp>

using Key = uint64_t;
using Payload = uint64_t;
using Clock = std::chrono::steady_clock;

#pragma pack(push, 1)
struct Op {
    uint8_t kind;   // 0 lookup, 1 insert, 2 range
    uint64_t key;
    uint32_t arg;   // range length in seconds
};
#pragma pack(pop)
static_assert(sizeof(Op) == 13, "trace record must be 13 bytes");

struct Phase {
    std::string name;
    std::vector<Op> ops;
};

static long rss_kb() {
    std::ifstream f("/proc/self/status");
    std::string line;
    while (std::getline(f, line))
        if (line.rfind("VmRSS:", 0) == 0) return std::stol(line.substr(6));
    return -1;
}

template <class T>
static void read_into(std::ifstream& f, T* dst, size_t n) {
    f.read(reinterpret_cast<char*>(dst), sizeof(T) * n);
    if (!f) throw std::runtime_error("truncated trace file");
}

// ------------------------------------------------------------------ index adapters
struct BTreeIndex {
    tlx::btree_map<Key, Payload> t;
    static const char* name() { return "btree"; }
    void bulk_load(std::vector<std::pair<Key, Payload>>& v) { t.bulk_load(v.begin(), v.end()); }
    bool insert(Key k, Payload p) { return t.insert(std::make_pair(k, p)).second; }
    bool lookup(Key k, Payload& out) {
        auto it = t.find(k);
        if (it == t.end()) return false;
        out = it->second;
        return true;
    }
    uint64_t range(Key lo, Key hi, uint64_t& sum) {
        uint64_t n = 0;
        for (auto it = t.lower_bound(lo); it != t.end() && it->first < hi; ++it) { sum += it->second; ++n; }
        return n;
    }
    std::string stats() const {
        auto s = t.get_stats();
        return "leaves=" + std::to_string(s.leaves) + ";inner_nodes=" + std::to_string(s.inner_nodes);
    }
};

struct AlexIndex {
    alex::Alex<Key, Payload> t;
    static const char* name() { return "alex"; }
    void bulk_load(std::vector<std::pair<Key, Payload>>& v) { t.bulk_load(v.data(), static_cast<int>(v.size())); }
    bool insert(Key k, Payload p) { return t.insert(k, p).second; }
    bool lookup(Key k, Payload& out) {
        Payload* p = t.get_payload(k);
        if (!p) return false;
        out = *p;
        return true;
    }
    uint64_t range(Key lo, Key hi, uint64_t& sum) {
        uint64_t n = 0;
        for (auto it = t.lower_bound(lo); it != t.end() && it.key() < hi; ++it) { sum += it.payload(); ++n; }
        return n;
    }
    std::string stats() const { return alex_stats(t); }

    static std::string alex_stats(const alex::Alex<Key, Payload>& t) {
        auto s = t.get_stats();
        return "model_nodes=" + std::to_string(s.num_model_nodes) + ";data_nodes=" + std::to_string(s.num_data_nodes) +
               ";expand_and_scales=" + std::to_string(s.num_expand_and_scales) +
               ";expand_and_retrains=" + std::to_string(s.num_expand_and_retrains) +
               ";downward_splits=" + std::to_string(s.num_downward_splits) +
               ";sideways_splits=" + std::to_string(s.num_sideways_splits) +
               ";model_bytes=" + std::to_string(t.model_size()) + ";data_bytes=" + std::to_string(t.data_size());
    }
};

// ALEX-HB (docs/experiment-phase4.md): inserts for sensors that suddenly become hot go to a small B+ tree
// buffer instead of ALEX; once no sensor is hot, each operation migrates up to M buffered keys into ALEX.
// Every key lives in exactly one structure, so lookups probe the buffer only for sensors with buffered keys
// and range scans simply add the two results.
struct HotBufferConfig {
    uint32_t window = 4096;   // W: recent inserts used to detect hot sensors
    uint32_t hot = 64;        // H: inserts within the window that make a sensor hot (cools below H/2)
    uint32_t migrate = 4;     // M: buffered keys moved into ALEX per operation once nothing is hot
};
static HotBufferConfig g_hb;

template <bool Migrate>
struct HotBufferAlex {
    alex::Alex<Key, Payload> t;
    tlx::btree_map<Key, Payload> buf;
    std::vector<uint32_t> ring;                       // sensor ids of the last W inserts
    size_t ring_pos = 0, ring_fill = 0;
    std::unordered_map<uint32_t, uint32_t> window;    // inserts per sensor within the window
    std::unordered_map<uint32_t, uint64_t> buffered;  // keys per sensor currently in the buffer
    std::unordered_set<uint32_t> hot;
    uint64_t routed = 0, migrated = 0, max_buffer = 0;

    static const char* name() { return Migrate ? "alexhb" : "alexhb-nomig"; }
    static uint32_t sensor(Key k) { return static_cast<uint32_t>(k >> 40); }

    void bulk_load(std::vector<std::pair<Key, Payload>>& v) {
        t.bulk_load(v.data(), static_cast<int>(v.size()));
        ring.assign(g_hb.window, 0);
    }

    void note_insert(uint32_t s) {
        if (ring_fill == ring.size()) {   // slide the window: forget the oldest insert
            const uint32_t old = ring[ring_pos];
            auto it = window.find(old);
            const uint32_t left = --it->second;
            if (left == 0) window.erase(it);
            if (left < g_hb.hot / 2) hot.erase(old);
        } else {
            ++ring_fill;
        }
        ring[ring_pos] = s;
        ring_pos = (ring_pos + 1) % ring.size();
        if (++window[s] >= g_hb.hot) hot.insert(s);
    }

    void maybe_migrate() {
        if (!Migrate || !hot.empty() || buf.empty()) return;
        for (uint32_t i = 0; i < g_hb.migrate && !buf.empty(); ++i) {
            auto it = buf.begin();
            t.insert(it->first, it->second);
            auto b = buffered.find(sensor(it->first));
            if (--b->second == 0) buffered.erase(b);
            buf.erase(it);
            ++migrated;
        }
    }

    bool insert(Key k, Payload p) {
        const uint32_t s = sensor(k);
        note_insert(s);
        bool ok;
        if (hot.count(s)) {
            ok = buf.insert(std::make_pair(k, p)).second;
            if (ok) {
                ++buffered[s];
                ++routed;
                max_buffer = std::max<uint64_t>(max_buffer, buf.size());
            }
        } else {
            ok = t.insert(k, p).second;
        }
        maybe_migrate();
        return ok;
    }

    bool lookup(Key k, Payload& out) {
        bool found = false;
        if (!buffered.empty() && buffered.count(sensor(k))) {
            auto it = buf.find(k);
            if (it != buf.end()) { out = it->second; found = true; }
        }
        if (!found) {
            Payload* p = t.get_payload(k);
            if (p) { out = *p; found = true; }
        }
        maybe_migrate();
        return found;
    }

    uint64_t range(Key lo, Key hi, uint64_t& sum) {
        uint64_t n = 0;
        for (auto it = t.lower_bound(lo); it != t.end() && it.key() < hi; ++it) { sum += it.payload(); ++n; }
        if (!buffered.empty() && buffered.count(sensor(lo)))   // a range never spans sensors (span < 2^40)
            for (auto it = buf.lower_bound(lo); it != buf.end() && it->first < hi; ++it) { sum += it->second; ++n; }
        maybe_migrate();
        return n;
    }

    std::string stats() const {
        return AlexIndex::alex_stats(t) + ";buffer_keys=" + std::to_string(buf.size()) +
               ";max_buffer=" + std::to_string(max_buffer) + ";routed=" + std::to_string(routed) +
               ";migrated=" + std::to_string(migrated) + ";hot_now=" + std::to_string(hot.size()) +
               ";W=" + std::to_string(g_hb.window) + ";H=" + std::to_string(g_hb.hot) +
               ";M=" + std::to_string(Migrate ? g_hb.migrate : 0);
    }
};

// ------------------------------------------------------------------ measurement
static uint64_t pct(std::vector<uint64_t>& v, double p) {
    if (v.empty()) return 0;
    size_t i = static_cast<size_t>(p * (v.size() - 1));
    std::nth_element(v.begin(), v.begin() + i, v.end());
    return v[i];
}

static uint64_t timer_overhead_ns() {
    std::vector<uint64_t> d(200000);
    for (auto& x : d) {
        auto a = Clock::now();
        auto b = Clock::now();
        x = std::chrono::duration_cast<std::chrono::nanoseconds>(b - a).count();
    }
    return pct(d, 0.5);
}

template <class Index>
static int run(const std::string& dir, int rep, const std::string& out_path) {
    std::vector<std::pair<Key, Payload>> bulk;
    std::vector<Phase> phases;
    {   // load traces before any timing
        std::ifstream f(dir + "/phases.bin", std::ios::binary);
        if (!f) { std::cerr << "cannot open " << dir << "/phases.bin\n"; return 2; }
        uint32_t np;
        read_into(f, &np, 1);
        for (uint32_t i = 0; i < np; ++i) {
            uint32_t len;
            read_into(f, &len, 1);
            Phase p;
            p.name.resize(len);
            f.read(&p.name[0], len);
            uint64_t n;
            read_into(f, &n, 1);
            p.ops.resize(n);
            read_into(f, p.ops.data(), n);
            phases.push_back(std::move(p));
        }
    }
    const long rss_base = rss_kb();
    {
        std::ifstream f(dir + "/bulk.bin", std::ios::binary);
        uint64_t n;
        read_into(f, &n, 1);
        std::vector<Key> keys(n);
        read_into(f, keys.data(), n);
        bulk.reserve(n);
        for (uint64_t i = 0; i < n; ++i) bulk.emplace_back(keys[i], i);
    }

    Index index;
    auto t0 = Clock::now();
    index.bulk_load(bulk);
    double load_s = std::chrono::duration<double>(Clock::now() - t0).count();
    const size_t bulk_n = bulk.size();
    std::vector<std::pair<Key, Payload>>().swap(bulk);   // give the bulk array back before measuring RSS

    const uint64_t overhead = timer_overhead_ns();
    std::ofstream out(out_path, std::ios::app);
    out.seekp(0, std::ios::end);
    if (out.tellp() == 0)
        out << "index,rep,phase,op,count,p50_ns,p95_ns,p99_ns,mean_ns,phase_ops_per_s,rss_index_mb,found,checksum,"
               "timer_overhead_ns,p999_ns,max_ns,tail_time_share,stats\n";
    auto mb = [&](long kb) { return (kb - rss_base) / 1024.0; };
    out << Index::name() << "," << rep << ",load,bulk_load," << bulk_n << ",0,0,0," << (load_s * 1e9 / bulk_n)
        << "," << (bulk_n / load_s) << "," << mb(rss_kb()) << ",0,0," << overhead << ",0," << (load_s * 1e9) << ",0,\""
        << index.stats() << "\"\n";

    std::vector<uint64_t> lat[3];
    Payload next_payload = 1ull << 40;   // payloads of inserted keys, identical across indexes
    for (auto& ph : phases) {
        for (auto& l : lat) { l.clear(); l.reserve(ph.ops.size()); }
        uint64_t found = 0, checksum = 0;
        auto phase_start = Clock::now();
        for (const Op& op : ph.ops) {
            auto a = Clock::now();
            if (op.kind == 0) {
                Payload p;
                if (index.lookup(op.key, p)) { ++found; checksum += p; }
            } else if (op.kind == 1) {
                index.insert(op.key, next_payload++);
            } else {
                found += index.range(op.key, op.key + op.arg, checksum);
            }
            auto b = Clock::now();
            lat[op.kind].push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(b - a).count());
        }
        double secs = std::chrono::duration<double>(Clock::now() - phase_start).count();
        const char* names[3] = {"lookup", "insert", "range"};
        const double rss = mb(rss_kb());
        for (int k = 0; k < 3; ++k) {
            auto& v = lat[k];
            if (v.empty()) continue;
            double total = 0;
            for (auto x : v) total += x;
            const double mean = total / v.size();
            const uint64_t p50 = pct(v, 0.5), p95 = pct(v, 0.95), p99 = pct(v, 0.99), p999 = pct(v, 0.999);
            const uint64_t mx = *std::max_element(v.begin(), v.end());
            double tail = 0;   // share of this operation type's total time spent in operations slower than p99
            for (auto x : v)
                if (x > p99) tail += x;
            out << Index::name() << "," << rep << ",\"" << ph.name << "\"," << names[k] << "," << v.size() << ","
                << p50 << "," << p95 << "," << p99 << "," << mean << "," << (ph.ops.size() / secs) << "," << rss << ","
                << found << "," << checksum << "," << overhead << "," << p999 << "," << mx << "," << (tail / total)
                << ",\"" << (k == 0 ? index.stats() : "") << "\"\n";
        }
        std::cerr << Index::name() << " rep " << rep << "  " << ph.name << ": " << static_cast<long>(ph.ops.size() / secs)
                  << " ops/s, found " << found << ", checksum " << checksum << "\n";
    }
    return 0;
}

int main(int argc, char** argv) {
    std::string index = "btree", dir = "traces", out = "results.csv";
    int rep = 0;
    for (int i = 1; i + 1 < argc; i += 2) {
        std::string a = argv[i];
        if (a == "--index") index = argv[i + 1];
        else if (a == "--traces") dir = argv[i + 1];
        else if (a == "--out") out = argv[i + 1];
        else if (a == "--rep") rep = std::stoi(argv[i + 1]);
        else if (a == "--hb-window") g_hb.window = static_cast<uint32_t>(std::stoul(argv[i + 1]));
        else if (a == "--hb-hot") g_hb.hot = static_cast<uint32_t>(std::stoul(argv[i + 1]));
        else if (a == "--hb-migrate") g_hb.migrate = static_cast<uint32_t>(std::stoul(argv[i + 1]));
    }
    if (index == "btree") return run<BTreeIndex>(dir, rep, out);
    if (index == "alex") return run<AlexIndex>(dir, rep, out);
    if (index == "alexhb") return run<HotBufferAlex<true>>(dir, rep, out);
    if (index == "alexhb-nomig") return run<HotBufferAlex<false>>(dir, rep, out);
    std::cerr << "unknown index " << index << "\n";
    return 2;
}
