# 1. 添加cmake版本说明
cmake_minimum_required(VERSION 3.1.3)
# 2. 声明工程名称
project(es_store_server)

set(target "es_store_server")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g")

# 3. 检测并生成ODB框架代码
#   1. 添加所需的proto映射代码文件名称
set(proto_path ${CMAKE_CURRENT_SOURCE_DIR}/../proto)
set(proto_files base.proto)
#   2. 检测框架代码文件是否已经生成
set(proto_hxx "")
set(proto_cxx "")
set(proto_srcs "")
foreach(proto_file ${proto_files})
#   3. 如果没有生成，则预定义生成指令 -- 用于在构建项目之间先生成框架代码
    string(REPLACE ".proto" ".pb.cc" proto_cc ${proto_file})
    string(REPLACE ".proto" ".pb.h" proto_hh  ${proto_file})
    if (NOT EXISTS ${CMAKE_CURRENT_BINARY_DIR}${proto_cc})
        add_custom_command(
            PRE_BUILD
            COMMAND protoc
            ARGS --cpp_out=${CMAKE_CURRENT_BINARY_DIR} -I ${proto_path} --experimental_allow_proto3_optional ${proto_path}/${proto_file}
            DEPENDS ${proto_path}/${proto_file}
            OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${proto_cc}
            COMMENT "生成Protobuf框架代码文件:" ${CMAKE_CURRENT_BINARY_DIR}/${proto_cc}
        )
    endif()
    list(APPEND proto_srcs ${CMAKE_CURRENT_BINARY_DIR}/${proto_cc})
endforeach()

set(odb_path ${CMAKE_CURRENT_SOURCE_DIR}/../odb)
set(odb_files )
set(odb_hxx "")
set(odb_cxx "")
set(odb_srcs "")
# 3. 检测并生成ODB框架代码（新版本）
set(odb_source_dir ${CMAKE_CURRENT_SOURCE_DIR}/../odb)
set(odb_binary_dir ${CMAKE_CURRENT_BINARY_DIR}/odb_generated)

# 创建生成目录
file(MAKE_DIRECTORY ${odb_binary_dir})

set(odb_srcs "")
foreach(odb_file ${odb_files})
    string(REPLACE ".hpp" "-odb.hxx" odb_hxx ${odb_file})
    string(REPLACE ".hpp" "-odb.cxx" odb_cxx ${odb_file})
    
    set(odb_cxx_output ${odb_binary_dir}/${odb_cxx})
    set(odb_hxx_output ${odb_binary_dir}/${odb_hxx})
    set(odb_source_file ${odb_source_dir}/${odb_file})
    
    # 检查源文件是否存在
    if(NOT EXISTS ${odb_source_file})
        message(FATAL_ERROR "ODB source file not found: ${odb_source_file}")
    endif()
    
    # 添加生成命令
    add_custom_command(
        OUTPUT ${odb_cxx_output} ${odb_hxx_output}
        COMMAND odb
            -d mysql
            --std c++11
            --generate-query
            --generate-schema
            --profile boost/date-time
            --output-dir ${odb_binary_dir}
            ${odb_source_file}
        DEPENDS ${odb_source_file}
        COMMENT "生成ODB框架代码: ${odb_cxx_output}"
    )
    
    # 添加到源文件列表
    list(APPEND odb_srcs ${odb_cxx_output})
endforeach()

# 添加头文件搜索路径
include_directories(${odb_binary_dir})

# 4. 获取源码目录下的所有源码文件
set(src_files "")
aux_source_directory(${CMAKE_CURRENT_SOURCE_DIR}/source src_files)
# 5. 声明目标及依赖
add_executable(${target} ${src_files} ${proto_srcs} ${odb_srcs})
# 7. 设置需要连接的库
target_link_libraries(${target} -lgflags 
    -lspdlog -lfmt -lbrpc -lssl -lcrypto 
    -lprotobuf -lleveldb -letcd-cpp-api 
    -lcpprest -lcurl -lodb-mysql -lodb -lodb-boost
    /usr/local/lib/libjsoncpp.so.1.8.4
    -lcpr -lelasticlient
    -lamqpcpp -lev)



# 6. 设置头文件默认搜索路径
include_directories(${CMAKE_CURRENT_BINARY_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../common)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../odb)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../third/include)

#8. 设置安装路径
INSTALL(TARGETS ${target}  RUNTIME DESTINATION bin)