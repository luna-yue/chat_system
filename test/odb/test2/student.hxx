#pragma once
#include <string>
#include <cstddef> // std::size_t
#include <boost/date_time/posix_time/posix_time.hpp>
#include <odb/nullable.hxx>
#include <odb/core.hxx>
#pragma db object
class Student
{
    public:
    Student() {}
    Student(unsigned long sn, const std::string &name, unsigned short age, unsigned long cid) : _sn(sn), _name(name), _age(age), _classes_id(cid) {}
    void sn(unsigned long num) { _sn = num; }
    unsigned long sn() { return _sn; }

    void name(const std::string &name) { _name = name; }
    std::string name() { return _name; }

    void age(unsigned short num) { _age = num; }
    odb::nullable<unsigned short> age() { return _age; }

    void classes_id(unsigned long cid) { _classes_id = cid; }
    unsigned long classes_id() { return _classes_id; }

private:
    friend class odb::access;
#pragma db id auto
    unsigned long _id;
#pragma db unique
    unsigned long _sn;
    std::string _name;
    odb::nullable<unsigned short> _age;
#pragma db index
    unsigned long _classes_id;
};
#pragma db object
class Classes
{
public:
    Classes() {}
    Classes(const std::string &name) : _name(name) {}
    void name(const std::string &name) { _name = name; }
    std::string name() { return _name; }
private:
    friend class odb::access;
#pragma db id auto
    unsigned long _id;
#pragma db unique type("VARCHAR(255)")
    std::string _name;
};
#pragma db view object(Student) object(Classes=classes : classes::_id==Student::_classes_id) query((?))
struct classes_student{
    #pragma db column(Student::_id)
    unsigned long id;
    #pragma db column(Student::_sn)
    unsigned long sn;
    #pragma db column(Student::_name)
    std::string name;
    #pragma db column(Student::_age)
    odb::nullable<unsigned short>age;
    #pragma db column(classes::_name)
    std::string classes_name;
};
//查询学生姓名，？为外部调用传入的过滤条件
#pragma db view query("select name from Student")
struct all_name {
    std::string name;
};
//odb -d mysql --std c++11 --generate-query --generate-schema --profile boost/date-time student.hxx