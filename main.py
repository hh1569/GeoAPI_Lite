from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 导入 CORS 中间件
from database import create_tables
from api import router_point,router_linestring,router_polygon,router_gis,router_user

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行：建表
    await create_tables()
    print("数据库表创建完成，FastAPI-GIS项目启动")
    yield
    # 关闭时执行：释放资源
    print("应用关闭，资源释放")

# FastAPI应用实例
app = FastAPI(
    title="FastAPI+PostGIS 平面位置管理系统",
    description="支持点位CRUD、附近查询、范围查询",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源访问
    allow_credentials=True,  # 允许携带认证信息
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(router_user)
app.include_router(router_point)
app.include_router(router_linestring)
app.include_router(router_polygon)
app.include_router(router_gis)

# 健康检查接口
@app.get("/", summary="健康检查")
async def health_check():
    return {"status": "ok", "message": "FastAPI-GIS服务运行正常"}

# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    #uvicorn api:app --reload --host 0.0.0.0 --port 8000