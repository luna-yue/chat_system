#include <gtest/gtest.h>
#include <iostream>
using namespace std;
int add(int a,int b)
{
    return a+b;
}
TEST(测试名称,加法)
{
    EXPECT_EQ(30,add(10,20));
    ASSERT_LT(30,add(10,30));
}
TEST(测试名称,字符串比较1)
{
   std::string tmp="hello";
   EXPECT_EQ("Hello",tmp);
   cout<<"is continue?1"<<endl;
   ASSERT_EQ("Hello",tmp);
   cout<<"is continue?2"<<endl;
}
TEST(测试名称,字符串比较2)
{
   std::string tmp="hello";
   EXPECT_EQ("Hello",tmp);
   cout<<"is continue?3"<<endl;
   ASSERT_EQ("Hello",tmp);
   cout<<"is continue?4"<<endl;
}
int main(int argc,char * argv[])
{
    testing::InitGoogleTest(&argc,argv);
    return RUN_ALL_TESTS();
}