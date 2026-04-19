# GeoAPI_Lite

> 基于 FastAPI + PostGIS 的轻量级矢量空间数据服务

## 功能

- 用户注册 / 登录，Bearer Token 认证
- 点、线、面空间要素的增删改查
- Excel 批量导入坐标数据
- 附近查询（ST_DWithin）与矩形范围查询（ST_Intersects）
- 标准 GeoJSON 输出，前端地图库可直接加载

## 技术栈

- Python 3.10+
- FastAPI（异步 Web 框架）
- PostgreSQL + PostGIS（空间数据库）
- SQLAlchemy 2.0 + GeoAlchemy2（异步 ORM）
- Shapely（几何对象处理）

## 快速开始

1. 克隆仓库
   git clone https://github.com/hh1569/GeoAPI_Lite.git
   cd GeoAPI_Lite

2. 启动服务
 python main.py
   
   
