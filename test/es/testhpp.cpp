#include "../../common/elasticSearch.hpp"
#include <gflags/gflags.h>
#include <unistd.h>
DEFINE_bool(run_mode, false, "程序的运行模式，false-调试； true-发布；");
DEFINE_string(log_file, "", "发布模式下，用于指定日志的输出文件");
DEFINE_int32(log_level, 0, "发布模式下，用于指定日志输出等级");

int main(int argc, char *argv[])
{

    google::ParseCommandLineFlags(&argc, &argv, true);
    init_logger(FLAGS_run_mode, FLAGS_log_file, FLAGS_log_level);

    std::vector<std::string> host_list = {"http://127.0.0.1:9200/"};
    auto client = std::make_shared<elasticlient::Client>(host_list);
    std::cout << (uint64_t)client.get() << std::endl;
    bool ret;
    ret = ESIndex(client, "test_user").append("nickname").append("phone", "keyword").create();
    if(!ret){
        LOG_ERROR("索引设置失败");
        return -1;
    }
    else{
        LOG_INFO("索引设置成功");
    }
    //新增数据
    ret=ESInsert(client,"test_user").append("nickname","luna")
    .append("phone","13963407683")
    .insert("00001");
    if(!ret)
    {
        LOG_ERROR("数据插入失败");
        return -1;
    }
    else
    {
        LOG_ERROR("数据插入成功");
    }
    //修改数据
    ret=ESInsert(client,"test_user").append("nickname","luna")
    .append("phone","19966667777")
    .insert("00001");
    if(!ret)
    {
        LOG_ERROR("数据修改失败");
        return -1;
    }
    else
    {
        LOG_ERROR("数据修改成功");
    }
    //sleep(5);
    Json::Value user = ESSearch(client, "test_user")
        .append_must_term("phone", "19966667777")
        .append_must_not_terms("nickname", {"kong"})
        .search();
    if (user.empty() || user.isArray() == false) {
        LOG_ERROR("结果为空，或者结果不是数组类型");
        return -1;
    } else {
        LOG_INFO("数据检索成功!");
    }
    int sz = user.size();
    LOG_DEBUG("检索结果条目数量：{}", sz);
    for (int i = 0; i < sz; i++) {
        LOG_INFO("nickname: {}", user[i]["_source"]["nickname"].asString());
    }

    ret = ESRemove(client, "test_user").remove("00001");
    if (ret == false) {
        LOG_ERROR("删除数据失败");
        return -1;
    }  else {
        LOG_INFO("数据删除成功!");
    }

}