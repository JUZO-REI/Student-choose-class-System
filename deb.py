import os
import sqlite3
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
from typing import Optional
from load import auth_router, require_admin, require_student


# 配置读取
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "sqlite").lower()

# SQLite 配置
DATABASE = "item.db"

# MySQL 配置 
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456") # 密码
MYSQL_DB = os.getenv("MYSQL_DB", "school_db")          # 库名

import pymysql
from pymysql.cursors import DictCursor

class CursorWrapper:
    def __init__(self, cursor, db_type):
        self.cursor = cursor
        self.db_type = db_type

    def __getattr__(self, name):
        # 转发 fetchone, fetchall, lastrowid 等属性给原生 cursor
        return getattr(self.cursor, name)

def getdb():# 数据库连接
    if STORAGE_TYPE == "mysql":
        conn = pymysql.connect(
            host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
            password=MYSQL_PASSWORD, database=MYSQL_DB,
            charset='utf8mb4', cursorclass=DictCursor
        )
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DATABASE, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 保持原有的字典取值方式
        try:
            yield conn
        finally:
            conn.close()

def initdb():# 初始化两套数据库
    # MySQL 的自增语法是 AUTO_INCREMENT，去掉 CHECK 用 ENUM 代替
    if STORAGE_TYPE == "mysql":
        conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB, charset='utf8mb4')
        cursor = conn.cursor()
        # MySQL 建表语法
        sqls = [
            """CREATE TABLE IF NOT EXISTS students (
                student_id INT PRIMARY KEY AUTO_INCREMENT,
                student_no VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                gender ENUM('男', '女') NOT NULL,
                class_name VARCHAR(50),
                code VARCHAR(50) NOT NULL,
                status ENUM('启用', '停用') DEFAULT '启用'
            )""",
            """CREATE TABLE IF NOT EXISTS courses (
                course_id INT PRIMARY KEY AUTO_INCREMENT,
                course_no VARCHAR(50) UNIQUE NOT NULL,
                course_name VARCHAR(50) NOT NULL,
                credit INT DEFAULT 2,
                teacher VARCHAR(50) NOT NULL,
                rongliang INT DEFAULT 5,
                status ENUM('open', 'close') DEFAULT 'open'
            )""",
            """CREATE TABLE IF NOT EXISTS enrollments (
                jilu_id INT PRIMARY KEY AUTO_INCREMENT,
                student_id INT NOT NULL,
                course_id INT NOT NULL,
                score FLOAT,
                student_no VARCHAR(50) NOT NULL,
                course_no VARCHAR(50) NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (course_id) REFERENCES courses(course_id),
                UNIQUE(student_id, course_id)
            )""",
            """CREATE TABLE IF NOT EXISTS admins (
                admin_id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) DEFAULT 'admin',
                password VARCHAR(50) DEFAULT 'admin123'
            )"""
        ]
        for sql in sqls:
            cursor.execute(sql)
        # 插入默认管理员
        cursor.execute("INSERT IGNORE INTO admins (username, password) VALUES ('admin', 'admin123')")
        conn.commit()
        conn.close()
        
    else:#SQLite 初始化代码
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS students 
        (student_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        student_no TEXT UNIQUE NOT NULL, 
        name TEXT NOT NULL, 
        gender TEXT CHECK(gender IN ('男', '女')), 
        class_name TEXT, 
        code TEXT NOT NULL, 
        status TEXT CHECK(status IN ('启用', '停用')) DEFAULT '启用')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS courses 
        (course_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        course_no TEXT UNIQUE NOT NULL, 
        course_name TEXT NOT NULL, 
        credit INTEGER DEFAULT 2, 
        teacher TEXT NOT NULL, 
        rongliang INTEGER DEFAULT 5, 
        status TEXT CHECK(status IN ('open', 'close')) DEFAULT 'open')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS enrollments 
        (jilu_id INTEGER PRIMARY KEY AUTOINCREMENT,
          student_id INTEGER NOT NULL, 
          course_id INTEGER NOT NULL, score REAL, 
          student_no INTEGER NOT NULL, course_no INTEGER NOT NULL, 
          FOREIGN KEY (student_id) REFERENCES students(student_id), 
          FOREIGN KEY (course_id) REFERENCES courses(course_id), UNIQUE(student_id, course_id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins 
        (admin_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT DEFAULT 'admin', 
        password TEXT DEFAULT 'admin123')''')
        try:
            cursor.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin123')")
        except sqlite3.IntegrityError:
            pass
        conn.commit()
        conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    initdb()
    yield

app = FastAPI(lifespan=lifespan)

print(STORAGE_TYPE)
class student_management(BaseModel):
    student_no:int
    name:str
    gender:str
    class_name:str
    @field_validator("name", "gender", "class_name", mode="before")#首尾去空＋防止空字符输入   mode默认after意味着先检查类型通过后在做处理，而before则先处理在检查
    @classmethod
    def strip_and_notempty(cls, v):#不需要你在客户端里手动调用看到@直接调用，v是从客户端接收的值，cls就是这个类
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("信息不得为空")
        return v
class return_student(BaseModel):
    student_id:int
    student_no:int
    name:str
    gender:str
    class_name:str
    code:str
    status:str
@app.post("/admin/student/add",response_model=return_student)#创建学生
def stu_add(st:student_management,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    codes=f"2026{st.class_name}{st.student_no}"
    cursor=CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("""INSERT INTO students(student_no,name,gender,class_name,code)VALUES(%s,%s,%s,%s,%s)""",
                       (st.student_no,st.name,st.gender,st.class_name,codes))#insert插入
    else :
        cursor.execute("""INSERT INTO students(student_no,name,gender,class_name,code)VALUES(?,?,?,?,?)""",
                               (st.student_no,st.name,st.gender,st.class_name,codes))
    db.commit()
    id=cursor.lastrowid
    return {
        "student_id":id,
        "student_no":st.student_no,
        "name":st.name,
        "gender":st.gender,
        "class_name":st.class_name,
        "code":codes,
        "status":"启用"
    }

class class_management(BaseModel):
    no:int
    name:str
    credit:Optional[int]=2
    teacher:str
    rongliang:Optional[int]=5 
    @field_validator("name", "teacher", mode="before")#首尾去空＋防止空字符输入   mode默认after意味着先检查类型通过后在做处理，而before则先处理在检查
    @classmethod
    def strip_and_notempty(cls, v):#不需要你在客户端里手动调用看到@直接调用，v是从客户端接收的值，cls就是这个类
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("该字段不能为空")
        return v
class return_class(BaseModel):
    course_id:int
    course_no:int
    course_name:str
    credit:int
    teacher:str
    rongliang:int
    status:str="open"
@app.post("/admin/class/add",response_model=return_class)#创建课程
def cla_add(cl:class_management,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor=CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_no = %s", (cl.no,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"课程号 {cl.no} 已存在，请勿重复添加！")
        cursor.execute("""INSERT INTO courses(course_no,course_name,credit,teacher,rongliang)VALUES(%s,%s,%s,%s,%s)""",
                (cl.no,cl.name,cl.credit,cl.teacher,cl.rongliang))#insert插入   credit直接写，有默认值兜底检测到none也没事
    else:
        cursor.execute("SELECT * FROM courses WHERE course_no = ?", (cl.no,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"课程号 {cl.no} 已存在，请勿重复添加！")
        cursor.execute("""INSERT INTO courses(course_no,course_name,credit,teacher,rongliang)VALUES(?,?,?,?,?)""",
                    (cl.no,cl.name,cl.credit,cl.teacher,cl.rongliang))
    db.commit()
    id=cursor.lastrowid
    cursor=db.cursor()
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_id = %s", (id,))
    else:
        cursor.execute("SELECT * FROM courses WHERE course_id = ?", (id,))
    return dict(cursor.fetchone())

class class_gengxin(BaseModel):
    course_no:Optional[int]=None
    course_name:Optional[str]=None
    credit:Optional[int]=2
    teacher:Optional[str]=None
    rongliang:Optional[int]=5
    status:Optional[str]=None 
    @field_validator("course_name", "teacher","status", mode="before")#首尾去空＋防止空字符输入   mode默认after意味着先检查类型通过后在做处理，而before则先处理在检查
    @classmethod
    def strip_and_notempty(cls, v):#不需要你在客户端里手动调用看到@直接调用，v是从客户端接收的值，cls就是这个类
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("该字段不能为空")
        return v
@app.patch("/admin/class/gengxin",response_model=return_class)#修改课程
def cla_gengxin(id:int,item:class_gengxin,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_id = %s", (id,))
    else:
        cursor.execute("SELECT * FROM courses WHERE course_id = ?", (id,))
    row = cursor.fetchone()#更新前的
    if row is None:#id这条消息不存在
        raise HTTPException(status_code=404, detail="Item not found")
    date=dict(row)#旧的数据条
    newdate=item.model_dump(exclude_unset=True)#仅选取用户传入的字段转字典
    if not newdate:
        raise HTTPException(status_code=400, detail="没有东西")
    setsql=[]
    values=[]
    if STORAGE_TYPE=="mysql":
        for key,value in newdate.items():#取出在字典里的键值对分别赋值
            setsql.append(f"{key}=%s")
            values.append(value)
            if  date.get(key)==value:
                raise  HTTPException(status_code=400, detail=f"不能重复修改{key}")
        cursor =CursorWrapper(db.cursor(),STORAGE_TYPE)
        if not setsql:
            return date
        sql=f"UPDATE courses SET {','.join(setsql)} WHERE course_id=%s"#动态拼接url    ''.join()只能拼接字符串，可以在任何可替代的里面但是值只能是字符串
    else:
        for key,value in newdate.items():#取出在字典里的键值对分别赋值
            setsql.append(f"{key}=?")
            values.append(value)
            if  date.get(key)==value:
                raise  HTTPException(status_code=400, detail=f"不能重复修改{key}")
        cursor =CursorWrapper(db.cursor(),STORAGE_TYPE)
        if not setsql:
            return date
        sql=f"UPDATE courses SET {','.join(setsql)} WHERE course_id=?"
    values.append(id)#不要忘记where里需要id的值
    cursor.execute(sql,tuple(values))
    db.commit()#提交更新，只要对数据库里的信息添加修改等操作都要提交
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_id = %s", (id,))#重新搜索并return
    else:
        cursor.execute("SELECT * FROM courses WHERE course_id = ?", (id,))
    return dict(cursor.fetchone())

@app.get("/admin/students/look",response_model=list[return_student])#查看学生
def get_all_students(db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.patch("/admin/students/xiugai/{student_no}",response_model=return_student)#启用或者停用
def toggle_student_status(student_no: str,sta:str,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM students WHERE student_no=%s", (student_no,))
        row=cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="学生不存在")
        if row['status']==sta:
            raise  HTTPException(status_code=400, detail=f"不能重复修改状态喵!")
        cursor.execute("UPDATE students SET status = %s WHERE student_no=%s",(sta,student_no))
        db.commit()
        cursor.execute("SELECT * FROM students WHERE student_no = %s", (student_no,))
    else:
        cursor.execute("SELECT * FROM students WHERE student_no=?", (student_no,))
        row=cursor.fetchone()
        if not row:
                    raise HTTPException(status_code=404, detail="学生不存在")
        if row['status']==sta:
                    raise  HTTPException(status_code=400, detail=f"不能重复修改状态喵!")
        cursor.execute("UPDATE students SET status = ? WHERE student_no=?",(sta,student_no))
        db.commit()
        cursor.execute("SELECT * FROM students WHERE student_no = ?", (student_no,))#重新搜索并return
    return dict(cursor.fetchone())

@app.patch("/admin/students/xiugaicode/{student_no}",response_model=return_student)#学生改密码
def toggle_student_code(student_no: str,cod:str,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_student)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM students WHERE student_no=%s", (student_no,))
        row=cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="学生不存在")
        if row['code']==cod:
            raise  HTTPException(status_code=400, detail=f"不能重复修改密码喵!")
        cursor.execute("UPDATE students SET code = %sWHERE student_no=%s",(cod,student_no))
        db.commit()
        cursor.execute("SELECT * FROM students WHERE student_no =%s", (student_no,))#重新搜索并return
    else:
        cursor.execute("SELECT * FROM students WHERE student_no=?", (student_no,))
        row=cursor.fetchone()
        if not row:
                    raise HTTPException(status_code=404, detail="学生不存在")
        if row['code']==cod:
                    raise  HTTPException(status_code=400, detail=f"不能重复修改密码喵!")
        cursor.execute("UPDATE students SET code = ? WHERE student_no=?",(cod,student_no))
        db.commit()
        cursor.execute("SELECT * FROM students WHERE student_no =?", (student_no,))#重新搜索并return
    return dict(cursor.fetchone())

@app.delete("/admin/courses/{course_id}")#删除课程  {}里面的内容是上传参数
def delete_course(course_id: int,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_id=%s", (course_id,))
    else:
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_id=?", (course_id,))
    row=cursor.fetchone()
    if row['count']> 0:#拿出来的是对象，对象[i]相当于索引取值等价于对象.这种写法，这里取出id看看有没有人选
        raise HTTPException(status_code=400, detail="该课程已有学生选课，无法删除，请先处理选课记录")
    if STORAGE_TYPE=="mysql":
        cursor.execute("DELETE FROM courses WHERE course_id=%s", (course_id,))
    else:
        cursor.execute("DELETE FROM courses WHERE course_id=?", (course_id,))
    db.commit()
    return {"message": "课程删除成功"}

@app.get("/admin/courses/{course_id}/students")#查看某一门课的选课学生
def get_course_students(course_id: int,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    # 联表查询,课程下的学生信息  on那句----用on将两个表的id串起来要求s里的id必须在e里也有  s那句--给students一个简便的名字 
    if STORAGE_TYPE=="mysql":    
        cursor.execute('''
            SELECT s.student_id, s.student_no, s.name, s.gender, s.class_name 
            FROM students s   
            JOIN enrollments e ON s.student_id = e.student_id 
            WHERE e.course_id=%s
        ''', (course_id,))
    else:
        cursor.execute('''
                    SELECT s.student_id, s.student_no, s.name, s.gender, s.class_name 
                    FROM students s   
                    JOIN enrollments e ON s.student_id = e.student_id 
                    WHERE e.course_id=?
                ''', (course_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/admin/courses/tongji")#统计
def tongji(db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_admin)):
    cursor=CursorWrapper(db.cursor(),STORAGE_TYPE)
    cursor.execute("""
        SELECT c.course_name, c.rongliang, COUNT(e.student_no) as enrolled_count
        FROM courses c
        LEFT JOIN enrollments e ON c.course_no = e.course_no
        GROUP BY c.course_no, c.course_name, c.rongliang
    """)
    rows= cursor.fetchall()
    a={}
    for row in rows: #原版 row 是一个元组：(course_name, rongliang, enrolled_count)取值用索引，新版不可以这样子，要么键取值
        a[row['course_name']]=[row['rongliang']-row['enrolled_count'],row['enrolled_count']]
    return a

@app.get("/courses/look")#查看课程
def get_all_courses(db:sqlite3.Connection=Depends(getdb)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    cursor.execute("SELECT * FROM courses")
    rows = cursor.fetchall()
    return [{"course_no":row["course_no"],"course_name":row["course_name"],"teacher":row["teacher"],"credit":row["credit"]} for row in rows]#这种单独的要输出的就别加py库了
#row虽然是对象但是sql3.row不支持点取法所以请像键法一样取值  *也可以换成要返回的三个字段然后输出的时候直接dict(row)

@app.get("/courses/sort/{choice}")#查看课程排序
def get_all_courses(choice:int,db:sqlite3.Connection=Depends(getdb)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if choice ==1:
        cursor.execute("SELECT * FROM courses ORDER BY credit DESC")
    elif choice ==2:#as 那句 --把计算的值临时塞到一个列里返回给前端
        cursor.execute('''SELECT c.course_id,c.course_no,c.course_name,c.teacher,c.credit,c.rongliang, (c.rongliang - COUNT(e.course_id)) AS shenyv 
                        FROM courses c 
                        LEFT JOIN enrollments e ON c.course_id = e.course_id
                        GROUP BY c.course_id
                        ORDER BY (c.rongliang - COUNT(e.course_id)) DESC''')
    else:
        raise HTTPException(status_code=500, detail="请输入正确的序号喵！！") 
    rows = cursor.fetchall()
    return [dict(row)for row in rows]

@app.get("/courses/detail_look")#详细搜索课程
def search_courses(keyword: str,db:sqlite3.Connection=Depends(getdb)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    search_str = f"%{keyword}%"
    if STORAGE_TYPE=="mysql":
        cursor.execute('''
            SELECT * FROM courses 
            WHERE course_name LIKE %s OR course_no LIKE %s OR teacher LIKE %s
        ''', (search_str, search_str, search_str))
    else:
        cursor.execute('''
                    SELECT * FROM courses 
                    WHERE course_name LIKE ? OR course_no LIKE ? OR teacher LIKE ?
                ''', (search_str, search_str, search_str))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/courses/{course_no}")#详细课程剩余名额
def get_course_detail(course_no: int,db:sqlite3.Connection=Depends(getdb)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_no=%s", (course_no,))
    else:
        cursor.execute("SELECT * FROM courses WHERE course_no=?", (course_no,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 查询已选人数，计算剩余名额
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_no=%s", (course_no,))
    else:
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_no=?", (course_no,))
    r=cursor.fetchone()
    enrolled_count = r['count']
    course_data = dict(row)#转字典
    course_data["remaining_capacity"] = course_data["rongliang"]-enrolled_count
    return {"message":f"剩余名额：{course_data["remaining_capacity"]}"}

@app.post("/admin/courses/{course_no}/enroll")#选课
def enroll_course(course_no: str,student_no:str,db:sqlite3.Connection=Depends(getdb),admin:dict=Depends(require_student)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_no=%s", (course_no,))
        cur_row=cursor.fetchone()
        cursor.execute("SELECT * FROM students WHERE student_no=%s", (student_no,))
        stu_row=cursor.fetchone()
    else:
        cur_row=cursor.execute("SELECT * FROM courses WHERE course_no=?", (course_no,)).fetchone()
        stu_row=cursor.execute("SELECT * FROM students WHERE student_no=?", (student_no,)).fetchone()
#检查课程是否存在及状态
    if not cur_row:
        raise HTTPException(status_code=404, detail="课程不存在")
    if cur_row["status"] != "open":
        raise HTTPException(status_code=400, detail="选课失败：该课程未开放选课")
# 检查是否已经选过 
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM enrollments WHERE student_id=%s AND course_id=%s", (stu_row["student_id"], cur_row["course_id"]))
    else:
        cursor.execute("SELECT * FROM enrollments WHERE student_id=? AND course_id=?", (stu_row["student_id"], cur_row["course_id"]))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="选课失败：你已选择过该课程")
# 3. 检查课程容量
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_id=%s", (cur_row["course_id"],))
    else:
        cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE course_id=?", (cur_row["course_id"],))
    r=cursor.fetchone()
    enrolled_count = r['count']
    if enrolled_count >= cur_row["rongliang"]:
        raise HTTPException(status_code=400, detail="选课失败：该课程已经满员")
# 4. 执行选课
    try:
        if STORAGE_TYPE=="mysql":
            cursor.execute("INSERT INTO enrollments (student_id, course_id,student_no,course_no) VALUES (%s,%s,%s,%s)", (stu_row["student_id"], cur_row["course_id"],student_no,course_no))
        else:
            cursor.execute("INSERT INTO enrollments (student_id, course_id,student_no,course_no) VALUES (?,?,?,?)", (stu_row["student_id"], cur_row["course_id"],student_no,course_no))
        db.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="选课失败，系统异常") 
    return {"message": "选课成功"}

@app.delete("/courses/{course_no}/tuike")#退课
def drop_course(course_no: str,student_no:str, db:sqlite3.Connection=Depends(getdb)):
    cursor = db.cursor()
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM courses WHERE course_no=%s", (course_no,))
        cur_row=cursor.fetchone()
        cursor.execute("SELECT * FROM students WHERE student_no=%s", (student_no,))
        stu_row=cursor.fetchone()#mysql不支持直接.fetch
    else:
        cur_row=cursor.execute("SELECT * FROM courses WHERE course_no=?", (course_no,)).fetchone()
        stu_row=cursor.execute("SELECT * FROM students WHERE student_no=?", (student_no,)).fetchone()
    if not cur_row or not stu_row:
        raise HTTPException(status_code=500, detail="退课失败：根本没有这课程，请输入正确的课程编号喵8！")
# 1. 检查选课记录是否存在
    if STORAGE_TYPE=="mysql":    
        cursor.execute("SELECT * FROM enrollments WHERE student_id=%s AND course_id=%s", (stu_row["student_id"], cur_row["course_id"]))
    else:
        cursor.execute("SELECT * FROM enrollments WHERE student_id=? AND course_id=?", (stu_row["student_id"], cur_row["course_id"]))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="退课失败：你未选择该课程")
# 2. 执行退课
    cursor.execute("DELETE FROM enrollments WHERE student_id=%s AND course_id=%s", (stu_row["student_id"], cur_row["course_id"]))
    db.commit()
    return {"message": "退选成功"}

@app.get("/student/me/courses")#查看自己已选课程
def get_my_courses(student_no:str,db:sqlite3.Connection=Depends(getdb)):
    cursor = CursorWrapper(db.cursor(),STORAGE_TYPE) 
    print(type(cursor))
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM students WHERE student_no=%s", (student_no,))
        stu_row=cursor.fetchone()
        if stu_row:
            stu_row=dict(stu_row)
            # 联表查询自己已选的课程详细信息    下面第一行----这些是要拿取出来的字段
        cursor.execute('''
                    SELECT c.*, e.jilu_id       
                    FROM courses c
                    JOIN enrollments e ON c.course_id = e.course_id
                    WHERE e.student_id = %s
                ''', (stu_row["student_id"],))
    else :
        cursor.execute("SELECT * FROM students WHERE student_no=?", (student_no,))
        stu_row=cursor.fetchone()
        if stu_row:
            stu_row=dict(stu_row)
    # 联表查询自己已选的课程详细信息    下面第一行----这些是要拿取出来的字段
        cursor.execute('''
        SELECT c.*, e.jilu_id       
        FROM courses c
        JOIN enrollments e ON c.course_id = e.course_id
        WHERE e.student_id = ?
        ''', (stu_row["student_id"],))#只要学生id的这一条记录
    rows = cursor.fetchall()#拿去的课程信息和选课记录序号
    return [dict(row) for row in rows]

app.include_router(auth_router)#搭载一下鉴权 