# GeoAPI

基于 **FastAPI + PostGIS** 的空间数据管理服务，支持点（Point）、线（LineString）、面（Polygon）三种几何要素的增删改查、空间查询、坐标转换、数据导入导出。

---

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 14+ + PostGIS 3+ 扩展

### 安装

```bash
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env`：

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=your_database
POOL_SIZE=5
MAX_OVERFLOW=10
ECHO_SQL=False
```

### 启动

```bash
python main.py
```

服务启动后访问：
- API 文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/

---

## 使用流程

### 1. 注册用户

```http
POST /user/register
Content-Type: application/json

{
    "name": "test",
    "password": "123456",
    "phone": "13800000000"
}
```

### 2. 登录获取 Token

```http
POST /user/login?account=test&password=123456
```

响应：

```json
{
    "access_token": "dbb36607-2d3f-4fd2-a...",
    "token_type": "bearer",
    "user_id": 1
}
```

之后所有接口在请求头中携带：`Authorization: Bearer <access_token>`

### 3. 创建点位

```http
POST /api/point/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "天安门",
    "address": "北京市东城区",
    "geom": "POINT(116.4 39.9)",
    "coord_sys": 4326
}
```

### 4. 空间查询 — 附近点位

```http
POST /api/gis/nearby?output_coord_sys=4326
Authorization: Bearer <token>
Content-Type: application/json

{
    "lon": 116.4,
    "lat": 39.9,
    "radius": 5000
}
```

返回中心点周围 5 公里内所有点位、线、面要素。

### 5. 导出数据

```http
GET /api/gis/export?layer=point&format=xlsx
Authorization: Bearer <token>
```

支持 GeoJSON、CSV、Excel 三种格式，可指定要素 ID 和输出坐标系。

---

## API 完整列表

### 用户模块 `/user`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/user/register` | 注册新用户 | 否 |
| POST | `/user/login` | 登录获取 Token | 否 |
| PUT | `/user/update` | 修改用户信息 | 是 |
| PUT | `/user/password` | 修改密码 | 是 |

### 点位 `/api/point`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/point/` | 创建点位 | 是 |
| GET | `/api/point/list` | 查询所有点位（分页） | 是 |
| GET | `/api/point/{id}` | 按 ID 查询点位 | 是 |
| PUT | `/api/point/{id}` | 更新点位 | 是 |
| DELETE | `/api/point/{id}` | 删除点位 | 是 |

### 线 `/api/linestring`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/linestring/` | 创建线 | 是 |
| GET | `/api/linestring/list` | 查询所有线（分页） | 是 |
| GET | `/api/linestring/{id}` | 按 ID 查询线 | 是 |
| PUT | `/api/linestring/{id}` | 更新线 | 是 |
| DELETE | `/api/linestring/{id}` | 删除线 | 是 |

### 面 `/api/polygon`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/polygon/` | 创建面 | 是 |
| GET | `/api/polygon/list` | 查询所有面（分页） | 是 |
| GET | `/api/polygon/{id}` | 按 ID 查询面 | 是 |
| PUT | `/api/polygon/{id}` | 更新面 | 是 |
| DELETE | `/api/polygon/{id}` | 删除面 | 是 |

### 空间分析 `/api/gis`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/gis/summary` | 统计各图层要素数量 | 是 |
| POST | `/api/gis/nearby` | 附近查询（半径） | 是 |
| POST | `/api/gis/bbox` | 矩形范围查询 | 是 |
| GET | `/api/gis/intersect` | 要素相交查询 | 是 |
| GET | `/api/gis/include` | 要素包含查询 | 是 |
| GET | `/api/gis/distance` | 两要素距离计算 | 是 |
| GET | `/api/gis/transform` | 坐标转换 | 是 |
| GET | `/api/gis/{line_id}/length` | 计算线长度 | 是 |
| GET | `/api/gis/{polygon_id}/area` | 计算面积 | 是 |
| GET | `/api/gis/export` | 导出数据（GeoJSON/CSV/Excel） | 是 |
| POST | `/api/gis/batch/import-excel` | 从 Excel 批量导入 | 是 |

---

## 坐标系支持

| SRID | 名称 | 说明 |
|------|------|------|
| 4326 | WGS84 | GPS 全球坐标（默认） |
| 4490 | CGCS2000 | 中国国家大地坐标系 |
| 3857 | Web Mercator | 网络地图投影（单位：米） |

查询时可传 `output_coord_sys` 参数指定输出坐标系，不传则返回原始坐标。导入时可在 Excel 中加 `coord_sys` 列指定每行的坐标系。

---

## 项目结构

```
GeoAPI/
├── main.py               # 应用入口，路由注册
├── api.py                # 所有 API 端点定义
├── models.py             # SQLAlchemy ORM 模型
├── database.py           # 异步数据库引擎与会话
├── config.py             # 环境变量配置
├── requirements.txt      # Python 依赖
├── crud/
│   ├── crud_POINT.py     # 点位数据库操作
│   ├── crud_LINESTRING.py
│   ├── crud_POLYGON.py
│   ├── crud_user.py      # 用户操作
│   ├── crud_token.py     # Token 管理
│   └── gis.py            # 空间查询、导入导出、统计
├── schemas/
│   ├── schemas_POINT.py  # 点位请求/响应模型
│   ├── schemas_LINESTRING.py
│   ├── schemas_POLYGON.py
│   ├── schemas_GIS.py    # 空间查询请求模型
│   └── schemas_USER.py
└── utils/
    ├── auth.py           # Bearer Token 认证
    ├── geojson.py        # GeoJSON FeatureCollection 转换
    ├── encryption.py     # Bcrypt 密码哈希
    └── mapping_table.py  # 图层名称 → ORM 模型映射
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | PostgreSQL + PostGIS |
| ORM | SQLAlchemy 2.0 (async) + GeoAlchemy2 |
| 几何处理 | Shapely |
| 数据校验 | Pydantic v2 |
| 认证 | Bearer Token + Passlib / Bcrypt |
| 数据处理 | Pandas + OpenPyXL |
| 异步驱动 | asyncpg |

## License

MIT
