# GeoAPI_Lite

基于 **FastAPI + PostGIS** 的轻量级空间数据管理服务，支持点、线、面要素的 CRUD 操作及空间查询。

## 功能特性

- **空间要素管理**：支持 Point、LineString、Polygon 三类几何要素的增删改查
- **空间查询**：附近查询（半径范围）、范围查询（bbox）、要素集合导出
- **多坐标系支持**：4326（WGS84 GPS）、4490（CGCS2000 国家大地坐标系）、3857（Web 墨卡托投影），默认 4326
- **用户系统**：注册、登录、Token 认证、密码修改
- **数据导入导出**：支持 Excel 文件批量导入导出
- **GeoJSON 输出**：查询结果可导出为标准 GeoJSON 格式
- **CORS 支持**：默认允许跨域访问

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | PostgreSQL + PostGIS |
| ORM | SQLAlchemy 2.0 (async) + GeoAlchemy2 |
| 数据校验 | Pydantic v2 |
| 几何处理 | Shapely |
| 认证 | Token + Passlib/Bcrypt |
| 数据处理 | Pandas + OpenPyXL |

## 项目结构

```
GeoAPI_Lite/
├── main.py              # 应用入口
├── api.py               # 路由定义
├── models.py            # 数据库模型
├── database.py          # 数据库连接
├── config.py            # 配置管理
├── requirements.txt     # 依赖清单
├── schemas/             # Pydantic 数据模型
│   ├── schemas_POINT.py
│   ├── schemas_LINESTRING.py
│   ├── schemas_POLYGON.py
│   ├── schemas_GIS.py
│   └── schemas_USER.py
├── crud/                # 数据库操作
│   ├── crud_POINT.py
│   ├── crud_LINESTRING.py
│   ├── crud_POLYGON.py
│   ├── gis.py
│   ├── crud_user.py
│   └── crud_token.py
└── utils/               # 工具函数
    ├── auth.py          # 认证中间件
    ├── geojson.py       # GeoJSON 转换
    ├── encryption.py    # 密码加密
    └── mapping_table.py # 图层映射
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- PostgreSQL + PostGIS 扩展

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database
POOL_SIZE=5
MAX_OVERFLOW=10
ECHO_SQL=False
```

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动，访问 `http://localhost:8000/docs` 查看 API 文档。

## API 概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 用户 | `/user` | 注册、登录、信息修改 |
| 点位 | `/api/point` | 点要素 CRUD |
| 线段 | `/api/linestring` | 线要素 CRUD |
| 面 | `/api/polygon` | 面要素 CRUD |
| GIS | `/api/gis` | 空间查询、导入导出 |

## License

MIT
