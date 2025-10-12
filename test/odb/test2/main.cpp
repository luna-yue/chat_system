#include <odb/database.hxx>
#include <odb/mysql/database.hxx>
#include "student.hxx"
#include "student-odb.hxx"
#include <gflags/gflags.h>

DEFINE_string(host, "127.0.0.1", "这是Mysql服务器地址");
DEFINE_int32(port, 0, "这是Mysql服务器端口");
DEFINE_string(db, "TestDB", "数据库默认库名称");
DEFINE_string(user, "root", "这是Mysql用户名");
DEFINE_string(pswd, "968745321", "这是Mysql密码");
DEFINE_string(cset, "utf8", "这是Mysql客户端字符集");
DEFINE_int32(max_pool, 3, "这是Mysql连接池最大连接数量");

void insert_classes(odb::mysql::database &db)
{
    try
    {
        odb::transaction trans(db.begin());
        Classes c1("一年级一班");
        Classes c2("一年级二班");
        db.persist(c1);
        db.persist(c2);
        // 提交事务
        trans.commit();
    }
    catch (std::exception &e)
    {
        std::cout << "插入数据出错:" << e.what() << '\n';
    }
}
void insert_student(odb::mysql::database &db)
{
    try
    {
        // 获取事务对象开启事务
        odb::transaction trans(db.begin());
        Student s1(1, "张三", 18, 1);
        Student s2(2, "李四", 19, 1);
        Student s3(3, "王五", 18, 1);
        Student s4(4, "赵六", 15, 2);
        Student s5(5, "刘七", 18, 2);
        Student s6(6, "孙八", 23, 2);
        db.persist(s1);
        db.persist(s2);
        db.persist(s3);
        db.persist(s4);
        db.persist(s5);
        db.persist(s6);
        // 5. 提交事务
        trans.commit();
    }
    catch (std::exception &e)
    {
        std::cout << "插入学生数据出错：" << e.what() << std::endl;
    }
}
void update_student(odb::mysql::database &db, Student &stu)
{
    try
    {
        // 获取事务对象开启事务
        odb::transaction trans(db.begin());
        db.update(stu);
        //  提交事务
        trans.commit();
    }
    catch (std::exception &e)
    {
        std::cout << "更新学生数据出错：" << e.what() << std::endl;
    }
}
Student select_student(odb::mysql::database &db)
{
    Student res;
    try
    {
        // 获取事务对象开启事务
        odb::transaction trans(db.begin());
        typedef odb::query<Student> query;
        typedef odb::result<Student> result;
        result r(db.query<Student>(query::name == "张三"));
        if (r.size() != 1)
        {
            std::cout << "数据量不对！\n";
            return Student();
        }
        res = *r.begin();
        // 提交事务
        trans.commit();
    }
    catch (std::exception &e)
    {
        std::cout << "更新学生数据出错：" << e.what() << std::endl;
    }
    return res;
}
void remove_student(odb::mysql::database &db)
{
    try {
        //获取事务对象开启事务
        odb::transaction trans(db.begin());
        typedef odb::query<Student> query;
        db.erase_query<Student>(query::classes_id == 2);
        // 提交事务
        trans.commit();
    }catch (std::exception &e) {
        std::cout << "更新学生数据出错：" << e.what() << std::endl;
    }
}
// 查询视图
void classes_student(odb::mysql::database &db)
{
    try
    {
        // 获取事务对象开启事务
        odb::transaction trans(db.begin());
        typedef odb::query<struct classes_student> query;
        typedef odb::result<struct classes_student> result;
        result r(db.query<struct classes_student>(query::classes::id == 1));
        for (auto it = r.begin(); it != r.end(); ++it)
        {
            std::cout << it->id << std::endl;
            std::cout << it->sn << std::endl;
            std::cout << it->name << std::endl;
            std::cout << *it->age << std::endl;
            std::cout << it->classes_name << std::endl;
        }
        // 5. 提交事务
        trans.commit();
    }
    catch (std::exception &e)
    {
        std::cout << "更新学生数据出错：" << e.what() << std::endl;
    }
}

void all_student(odb::mysql::database &db)
{
    try {
        //获取事务对象开启事务
        odb::transaction trans(db.begin());
        typedef odb::query<Student> query;
        typedef odb::result<struct all_name> result;
        result r(db.query<struct all_name>(query::id == 1));
        for (auto it = r.begin(); it != r.end(); ++it) {
            std::cout << it->name << std::endl;
        }
        
        trans.commit();
    }catch (std::exception &e) {
        std::cout << "查询所有学生姓名数据出错：" << e.what() << std::endl;
    }
}

int main(int argc, char *argv[])
{

    google::ParseCommandLineFlags(&argc, &argv, true);
    // 什么是连接池工厂（connection_pool_factory）
    // connection_pool_factory 是一个「连接池的工厂类」，负责创建和管理一个连接池对象。
    // 它的核心目的就是：
    // 在程序启动时创建一批数据库连接，并重复使用它们，从而避免频繁建立/关闭连接的性能消耗。
    // 用unique ptr 原因 因为 odb::mysql::database 的构造函数期望接收一个 独占所有权的连接池工厂对象，
    // 这样它就能在内部持有并管理连接池生命周期。
    std::unique_ptr<odb::mysql::connection_pool_factory> cpf(
        new odb::mysql::connection_pool_factory(FLAGS_max_pool, 0));
    odb::mysql::database db(
        FLAGS_user, FLAGS_pswd, FLAGS_db,
        FLAGS_host, FLAGS_port, "", FLAGS_cset,
        0, std::move(cpf));
    insert_classes(db);
    insert_student(db);
    auto stu=select_student(db);
     std::cout << stu.sn() << std::endl;
    std::cout << stu.name() << std::endl;
    if (stu.age()) std::cout << *stu.age() << std::endl;
    std::cout << stu.classes_id() << std::endl;

    stu.age(15);
    update_student(db, stu);
    remove_student(db);
    //classes_student(db);
    all_student(db);
}