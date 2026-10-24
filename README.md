~~~text
一、deb.py是数据库文件
二、load.py是登录系统文件
三、client.py是用户操作端文件
四、item.db是sqlite测试的时候创建的文件
五、school_db是mysql用的数据库文件，在终端上由指令创建
~~~~
***一、接口地址***
~~~text
==========deb.py===========
1.POST /admin/student/add 创建学生
2.POST /admin/class/add 创建课程
3.PATCH /admin/class/gengxin 修改课程
4.GET /admin/students/look 查看学生
5.PATCH /admin/students/xiugai/{student_no} 启用或停用学
6.PATCH /adin/students/xiugaicode/{student_no} 学生改密码
7.DELETE /admin/courses/{course_id} 删除课程
8.GET /admin/courses/{course_id}/students 查看某一门课的选课的学生
9.GET /admin/courses/tongji 统计所有课的选课情况
10.GET /courses/look 查看所有课程
11.GET /courses/sort/{choice} 课程排序
12.GET /courses/detail_look 关键词搜索课程
13.GET /courses/{course_no} 查看课程剩余名额
14.POST /admin/courses/{course_no}/enroll 选课
15.DELETE /courses/{course_no}/tuike 退课
16.GET /student/me/courses 查看已选课程
==========load.py==========
1.POST /login 登录路由
~~~
***二、菜单***
~~~text
============学生============
1. 查看所有课程(支持按学分或者剩余容量排序)")
2. 详细搜索课程
3. 查看课程剩余名额
4. 选课
5. 退课 
6. 查看我的课程
7. 修改密码
8. 退出登录
===========管理员===========
1.创建学生
2.查看学生
3.启用或停用学生
4.创建课程
5.修改课程
6.删除课程
7.查看课程选课名单
8.查看课程列表
9.查看课程选课统计
10.退出登录
~~~
***三、启动顺序以及流程***
==🔵声明：支持终端命令行控制，支持MySQL与splite自主切换==
~~~text
1先启动deb.py
	·mysql
	cd 文件所在文件夹-->$env:STORAGE_TYPE="mysql"-->（echo $env:STORAGE_TYPE  可检查类型）--> uvicorn deb:app --reload
	·sqlite
	cd 文件所在文件夹-->$env:STORAGE_TYPE="sqlite"-->（echo $env:STORAGE_TYPE  可检查类型）--> uvicorn deb:app --reload
2命令终端
	cd 文件所在文件夹-->python client.py
3终止服务器
	ctrl+c即可
~~~
==🔴注：启动服务器用的vscode提供的PowerShell环境，启动客户端用的本机CMD控制端==
