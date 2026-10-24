from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import sqlite3
import os
import pymysql
from pymysql.cursors import DictCursor

# ================= 1. 配置读取 (必须和 deb.py 保持一致) =================
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "sqlite").lower()
DATABASE = "item.db"

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456") # 记得改成你的密码
MYSQL_DB = os.getenv("MYSQL_DB", "school_db")

# ================= 2. 动态数据库连接 =================
def get_db():
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
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

auth_router = APIRouter()

ACTIVE_TOKENS = {}#内存 Token 存储 
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

#鉴权依赖   deb里遇到这个的依赖包先进b或c然后遇到a的依赖包进a然后进15去请求
def get_current_user(token: str = Depends(api_key_header)):#a
    if not token or token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="未登录或登录已失效，请重新登录喵")
    return ACTIVE_TOKENS[token]
def require_admin(user: dict = Depends(get_current_user)):#b
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="权限不足，只有管理员可以执行此操作喵")
    return user
def require_student(user: dict = Depends(get_current_user)):#c
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="权限不足，只有学生可以执行此操作喵")
    return user

class LoginModel(BaseModel):#登录数据
    username: str
    password: str 

@auth_router.post("/login")#登录路由
def universal_login(data: LoginModel,db:sqlite3.Connection=Depends(get_db)):
    cursor = db.cursor()
    
    try:
        if STORAGE_TYPE=="mysql":
            cursor.execute("SELECT * FROM admins WHERE username=%s AND password=%s", (data.username, data.password))
        else:
            cursor.execute("SELECT * FROM admins WHERE username=? AND password=?", (data.username, data.password))
        admin = cursor.fetchone()
        if admin:
            token = f"TOKEN_admin_{admin['admin_id']}"
            ACTIVE_TOKENS[token] = {"role": "admin","id":admin["admin_id"], "name": admin['username']}
            return {"message": "管理员登录成功", "token": token, "role": "admin"}
    except sqlite3.OperationalError:
        raise HTTPException(status_code=401, detail="用户名或密码错误喵")

    # 检查学生 (对应你原有的 students 表)
    if STORAGE_TYPE=="mysql":
        cursor.execute("SELECT * FROM students WHERE student_no=%s AND code=%s", (data.username, data.password))
    else:
        cursor.execute("SELECT * FROM students WHERE student_no=? AND code=?", (data.username, data.password))
    student = cursor.fetchone()   
    if student and student['status']=="停用":
        raise HTTPException(status_code=401, detail="你不可以登录喵！")
    if student:
        token = f"TOKEN_student_{student['student_id']}"
        ACTIVE_TOKENS[token] = {"role": "student", "student_no": student['student_no'], "name": student['name']}
        return {"message": "学生登录成功", "token": token, "role": "student"}
    raise HTTPException(status_code=401, detail="用户名或密码错误,如是新用户请找管理员添加喵")