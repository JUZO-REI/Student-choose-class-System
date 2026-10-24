import requests
import os
os.environ["NO_PROXY"] = "*"  # 强制让 Python 忽略所有系统代理   cmd使用

addre="http://localhost:8000"

MY_TOKEN=None
MY_ROLE=None

# 通用请求工具
def send_request(method, path, json_data=None,params=None):#method是你要提交修改等动作，path是你动作的那个地址
    # 自动拼请求头
    headers = {}
    if MY_TOKEN:
        headers["Authorization"] = MY_TOKEN
        
    url = f"{addre}{path}"
    
    if method.upper() == "GET":
        return requests.get(url, headers=headers,params=params)#get统一用params
    elif method.upper() == "POST":
        return requests.post(url, json=json_data, headers=headers)#post用json
    elif method.upper() == "DELETE":
        return requests.delete(url, headers=headers)
    elif method.upper()=="PATCH":
        return requests.patch(url,json=json_data, headers=headers)

def do_login():#登录系统入口
    global MY_ROLE,MY_TOKEN
    no=input("请输入你的账号(学号或者管理号)")
    code=input("请输入你的密码")
    try:
        iden=requests.post(f"{addre}/login",json={"username":no,"password":code})#直接传字典
        if iden.status_code==200:#登上了
            data=iden.json()
            MY_TOKEN=data["token"]#存入临时id与身份
            MY_ROLE=data["role"]
            print(f"{data['message']}，欢迎你！")
            return no  
        else:
            # 如果密码错了，后端会返回 401
            error_msg = iden.json().get("detail", "未知错误")
            print(f"登录失败: {error_msg}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("无法连接到服务器，请确认 FastAPI 后端是否已启动！")
        return False

def student_menu():
    """学生登录后看到的菜单"""
    print("\n==== 学生菜单 ====")
    print("1. 查看所有课程(支持按学分或者剩余容量排序)")
    print("2. 详细搜索课程")
    print("3. 查看课程剩余名额")
    print("4. 选课")
    print("5. 退课 ")
    print("6. 查看我的课程")
    print("7. 修改密码")
    print("8. 退出登录")
    

def admin_menu():
    """管理员登录后看到的菜单"""
    print("\n==== 管理员菜单 ====")
    print("1. 创建学生")
    print("2. 查看学生")
    print("3. 启用或停用学生")
    print("4. 创建课程")
    print("5. 修改课程")
    print("6. 删除课程")
    print("7. 查看课程选课名单")
    print("8. 查看课程列表")
    print("9. 查看课程选课统计")
    print("10. 退出登录")

def main():
    global MY_ROLE,MY_TOKEN,no
    while True:
        if not MY_TOKEN:
            print("===== 校园选课系统 =====")
            print("1.登录")
            print("0.退出")
            choose=input("请选择:")
            if choose=="1":
                no=do_login()        
            elif choose=="0":
                print("谢谢使用喵！")
                break
            else:
                print("请输入正确的选项喵！！！")
        else:
            if MY_ROLE=="student":
                student_menu()
                chooses=input("请输入:")
                if chooses=="8":
                    MY_TOKEN=None
                    MY_ROLE=None
                    print("感谢使用喵！")
                    break
                elif chooses=="1":
                    c=int(input("直接查找请按1，按学分或剩余名额请按2:"))
                    if c==1:
                        res = send_request("GET", "/courses/look")
                        if res.status_code == 200:
                            courses = res.json()
                            print("\n--- 课程列表 ---")
                            for c in courses:
                                print(f"课程号: {c['course_no']} | 课名: {c['course_name']} | 教师: {c['teacher']}")
                        else:
                            print(f"获取失败: {res.json().get('detail')}")
                    elif c==2:
                        c1=int(input("按学分按1，按剩余名额按2："))
                        res = send_request("GET", f"/courses/sort/{c1}")
                        if res.status_code == 200:
                            courses = res.json()
                            print("\n--- 课程列表 ---")
                            if c1==1:
                                for c2 in courses:
                                    print(f"课程号: {c2['course_no']} | 课名: {c2['course_name']} | 教师: {c2['teacher']}| 学分：{c2['credit']}| 容量：{c2['rongliang']}")
                            elif c1==2:
                                for c2 in courses:
                                    print(f"课程号: {c2['course_no']} | 课名: {c2['course_name']} | 教师: {c2['teacher']}| 学分：{c2['credit']}| 剩余容量：{c2['shenyv']}")
                        else:
                            print(f"获取失败: {res.json().get('detail')}")
                    else:
                        print("获取失败: 请输入正确的序号喵！")
                elif chooses=="2":
                    keyword = input("请输入关键词 (课程名/编号/教师): ")
                    res = send_request("GET", f"/courses/detail_look?keyword={keyword}")#不是类且不属于路径的单个参数要先这样子拼上去
                    if res.status_code == 200:
                        courses = res.json()
                        print(f"\n--- 搜索结果 (共 {len(courses)} 条) ---")
                        for c in courses:
                            print(f"课程序列号: {c['course_id']}| 学分: {c['credit']}| 老师: {c['teacher']}| 容量: {c['rongliang']}| 状态: {c['status']}| 课程号: {c['course_no']} | 课名: {c['course_name']}")
                    else:
                        print(f"搜索失败: {res.json().get('detail')}")
                elif chooses=="3":
                    course_no = input("请输入要查看的课程编号: ")
                    res = send_request("GET", f"/courses/{course_no}")
                    if res.status_code == 200:
                        print(res.json().get('message'))
                    else:
                        print(f"查询失败: {res.json().get('detail')}")
                elif chooses=="4":
                    course_no = input("请输入要选课的课程编号: ")
                    res = send_request("POST", f"/admin/courses/{course_no}/enroll?student_no={no}")
                    if res.status_code == 200:
                        print(res.json().get('message'))
                    else:
                        print(res.json().get('detail'))# 这里会接住返回的各种错误（满员、未开放、已选过）
                elif chooses=="5":
                    course_no = input("请输入要退选的课程编号: ")
                    res = send_request("DELETE", f"/courses/{course_no}/tuike?student_no={no}")
                    if res.status_code == 200:
                        print(res.json().get('message'))
                    else:
                        print(res.json().get('detail'))

                elif chooses=="6":
                    res = send_request("GET", "/student/me/courses",params={"student_no":no})#也可以拼在路径上  no是登录函数的局部变量将局部变量返回到这里就可以使用了
                    if res.status_code == 200:
                        courses = res.json()
                        if not courses:
                            print("你还没有选课喵~")
                        else:
                              print("\n--- 我的已选课程 ---")
                        for c in courses:
                            print(f"课程号: {c['course_no']} | 课名: {c['course_name']} | 教师: {c['teacher']}")
                    else:
                        print(f"获取失败: {res.json().get('detail')}")
                elif chooses=="7":
                    cod = input("请输入新密码: ")
                    res = send_request("PATCH", f"/admin/students/xiugaicode/{no}?cod={cod}")
                    if res.status_code == 200:
                        print("密码修改成功！")
                    else:
                        print(res.json().get('detail'))
                else:
                    print("请输入正确的选项喵！！！")
            if MY_ROLE=="admin":
                admin_menu()
                chooses=input("请输入：")
                if chooses=="10":
                    MY_TOKEN=None
                    MY_ROLE=None
                    print("感谢使用喵！")
                    break
                elif chooses=="1":
                    print("\n--- 创建学生 ---")
                    try:
                        student_no = input("学号 (纯数字): ")
                        name = input("姓名: ")
                        gender = input("性别(男/女): ")
                        class_name = input("班级: ")
                        data = {"student_no": student_no, "name": name, "gender": gender, "class_name": class_name}#以字典的形式塞到那个类里
                        res = send_request("POST", "/admin/student/add", json_data=data)
                        if res.status_code == 200:
                            print(f"创建成功！序列号:{res.json().get('student_id')}| 学号: {res.json().get('student_no')}| 名字:{res.json().get('name')}| 性别：{res.json().get('gender')}| 班级：{res.json().get('class_name')}| 密码：{res.json().get('code')}| 状态：{res.json().get('status')}")
                        else:
                            print(f"失败: {res.json().get('detail')}")
                    except ValueError:
                        print("学号必须是纯数字！")

                elif chooses=="2":
                    res = send_request("GET", "/admin/students/look")
                    if res.status_code == 200:
                        students = res.json()#有很多字典的列表
                        print("\n--- 学生列表 ---")
                        for s in students:
                            print(f"序列号:{s.get('student_id')}|学号: {s['student_no']} | 姓名: {s['name']} | 班级: {s['class_name']} | 状态: {s.get('status')}| 密码: {s.get('code')}")
                    else:
                        print(f"获取失败: {res.json().get('detail')}")

                elif chooses=="3":
                    student_no = input("请输入要操作的学生学号: ")
                    sta = input("请输入新状态 (例如 '启用' 或 '停用'): ")
                    res = send_request("PATCH", f"/admin/students/xiugai/{student_no}?sta={sta}")
                    if res.status_code == 200:
                        print("状态修改成功！")
                    else:
                        print(res.json().get('detail'))
                elif chooses=="4":
                    print("\n--- 创建课程 ---")
                    try:
                        no = int(input("课程号 (纯数字): "))
                        name = input("课程名称: ")
                        teacher = input("任课教师: ")
                        cre=input("学分：（直接回车默认两分）")
                        credit = int(cre)if cre else 2
                        ron=input("容量：（直接回车默认五人）")
                        rongliang = int(ron)if ron else 5
                        data = {"no": no, "name": name, "teacher": teacher, "credit": credit, "rongliang": rongliang}
                        res = send_request("POST", "/admin/class/add", json_data=data)
                        if res.status_code == 200:
                            print("课程创建成功！")
                            print(f"序列号：{res.json().get('course_id')}|课程编号：{res.json().get('course_no')}| 课程名：{res.json().get('course_name')}| 学分：{res.json().get('credit')}| 教师：{res.json().get('teacher')}| 总容量：{res.json().get('rongliang')}| 状态：{res.json().get('status')}")
                        else:
                            print(f"失败: {res.json().get('detail')}")
                    except ValueError:
                        print("输入有误！")

                elif chooses=="5":
                    course_id = input("请输入要修改的课程序列号ID (course_id): ")
                    print("提示：这里可以根据需要输入要修改的字段，留空则不修改")
                    json_data = {}
                    new_name = input("新课程名称 (留空跳过): ")
                    new_no=input("新编号(留空跳过):")
                    if new_no:
                        new_no=int(new_no)
                    new_credit=input("新学分(留空跳过):")
                    if new_credit:
                        new_credit=int(new_credit)
                    new_teacher=input("新老师(留空跳过):")
                    new_rongliang=input("新容量(留空跳过):")
                    if new_rongliang:
                        new_rongliang=int(new_rongliang)
                    new_status=input("新状态(留空跳过):")
                    a=[new_no,new_name,new_credit,new_teacher,new_rongliang,new_status]
                    b=["course_no","course_name","credit","teacher","rongliang","status"]
                    for i in range (len(a)):
                        if a[i]: 
                            json_data[b[i]] = a[i]
                    res = send_request("PATCH", f"/admin/class/gengxin?id={course_id}", json_data=json_data)
                    if res and res.status_code == 200:
                        print("修改成功！")
                    else:
                        print(f"失败: {res.json().get('detail')}")

                elif chooses=="6":
                    course_id = input("请输入要删除的课程序列号ID: ")
                    res = send_request("DELETE", f"/admin/courses/{course_id}")
                    if res.status_code == 200:
                        print("删除成功！")
                    else:
                        print(f"删除失败: {res.json().get('detail')}")
                elif chooses=="7":
                    course_id = input("请输入要查看的课程序列号ID:")
                    res = send_request("GET", f"/admin/courses/{course_id}/students")
                    if res.status_code == 200:
                        students = res.json()
                        print(f"\n--- 选课名单 ---")
                        for s in students:
                            print(f"序列号:{s.get('student_id')}| 学号: {s['student_no']} | 姓名: {s['name']}")
                    else:
                        print(f"获取失败: {res.json().get('detail')}")
                elif chooses=="8":
                    res = send_request("GET", "/courses/look")
                    if res.status_code == 200:
                        courses = res.json()
                        print("\n--- 课程列表 ---")
                        for c in courses:
                            print(f"课程号: {c['course_no']} | 课名: {c['course_name']} | 教师: {c['teacher']}| 学分：{c['credit']}")
                    else:
                        print(f"获取失败: {res.json().get('detail')}")
                elif chooses=="9":
                    res = send_request("GET", "/admin/courses/tongji")
                    if res and res.status_code == 200:
                        re=res.json()#只要是http协议返回的字典就要用这个过度一下
                        for i in re:
                            print("====统计结果====")
                            print(f"课程：{i}:剩余：{re[i][0]}| 已报：{re[i][1]}")
                    else:
                        print("查看失败喵！")
                else:
                    print("请输入正确的选项喵！！！")

                
if __name__ == "__main__":
    main()