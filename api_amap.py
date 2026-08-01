"""
高德服务接口：把高德开放平台能力包装成项目自己的 API
只需调用本项目的接口即可获得高德数据，key 由项目统一管理

接口清单：
    GET  /api/amap/search           POI搜索（按类型码/关键词，返回 WGS84 坐标）
    POST /api/amap/search_import    POI搜索并一键导入数据库（point_feature 点表）
    GET  /api/amap/geocode          地理编码（地址 → 经纬度）
    GET  /api/amap/regeo            逆地理编码（经纬度 → 地址）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from crud.crud_LINESTRING import create_linestring
from crud.crud_POINT import create_point
from crud.crud_POLYGON import create_polygon
from database import get_db
from models import LinestringFeature, PointFeature, PolygonFeature, User
from schemas.schemas_LINESTRING import LinestringCreate
from schemas.schemas_POINT import PointCreate
from schemas.schemas_POLYGON import PolygonCreate
from utils import amap_client
from utils.auth import current_user

router_amap = APIRouter(prefix="/api/amap", tags=["Amap高德服务"])


@router_amap.get("/search", summary="POI搜索：查高德地图数据（不入库）")
async def amap_search(
    types: str | None = Query(None, description="高德POI类型码，如 1412=学校、060100=餐饮、080300=医院、050000=景点"),
    keywords: str | None = Query(None, description="关键词（按名称搜，与 types 二选一）"),
    city: str = Query("520400", description="城市名或adcode，默认520400=安顺市"),
    pages: int = Query(1, ge=1, le=10, description="抓取页数（每页25条）"),
    user: User = Depends(current_user),
):
    """查询高德并返回结果（坐标已转 WGS84），不写入数据库"""
    if not types and not keywords:
        raise HTTPException(status_code=400, detail="types 和 keywords 至少传一个")
    try:
        pois = amap_client.search_poi_many(keywords=keywords, types=types, city=city, pages=pages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    return {"total": len(pois), "items": pois}


@router_amap.post("/search_import", summary="POI搜索并导入数据库（写入点表）")
async def amap_search_import(
    types: str | None = Query(None, description="高德POI类型码，如 1412=学校、060100=餐饮"),
    keywords: str | None = Query(None, description="关键词（按名称搜，与 types 二选一）"),
    city: str = Query("520400", description="城市名或adcode，默认520400=安顺市"),
    pages: int = Query(1, ge=1, le=10, description="抓取页数（每页25条）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    查询高德 → 自动写入 point_feature 点表（归属当前登录用户）
    同名点位自动跳过（幂等），可重复执行
    """
    if not types and not keywords:
        raise HTTPException(status_code=400, detail="types 和 keywords 至少传一个")

    try:
        pois = amap_client.search_poi_many(keywords=keywords, types=types, city=city, pages=pages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")

    # 该用户已存在的点位名称，用于幂等跳过
    result = await db.execute(
        select(PointFeature.name).where(PointFeature.userid == user.userid)
    )
    existing = {row[0] for row in result.all()}

    inserted, skipped = 0, 0
    for poi in pois:
        if poi["name"] in existing:
            skipped += 1
            continue
        point = PointCreate(
            name=poi["name"],
            address=poi["address"] or f"{poi['province']}{poi['city']}{poi['district']}",
            geom=f"POINT({poi['lon']} {poi['lat']})",   # 已是 WGS84，与项目 4326 一致
            coord_sys=4326,
        )
        await create_point(db, user.userid, point)
        existing.add(poi["name"])
        inserted += 1

    return {
        "fetched": len(pois),       # 高德查到的条数
        "inserted": inserted,       # 本次新入库
        "skipped": skipped,         # 已存在跳过的
        "message": f"导入完成：新增 {inserted} 条，跳过重复 {skipped} 条",
    }


@router_amap.get("/geocode", summary="地理编码：地址 → 经纬度(WGS84)")
async def amap_geocode(
    address: str = Query(..., description="地址文本，如：安顺学院"),
    city: str | None = Query(None, description="限定城市（可选），如：安顺市"),
    user: User = Depends(current_user),
):
    """地址转坐标，返回 WGS84 经纬度"""
    try:
        items = amap_client.geocode(address=address, city=city)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    return {"total": len(items), "items": items}


@router_amap.get("/regeo", summary="逆地理编码：经纬度(WGS84) → 地址")
async def amap_regeo(
    lon: float = Query(..., ge=-180, le=180, description="经度(WGS84)"),
    lat: float = Query(..., ge=-90, le=90, description="纬度(WGS84)"),
    user: User = Depends(current_user),
):
    """坐标转地址，输入 WGS84（项目标准），内部自动转火星坐标请求高德"""
    try:
        result = amap_client.regeo(lon=lon, lat=lat)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    return result


# ------------------------------
# 面数据：行政区划边界
# ------------------------------
@router_amap.get("/district", summary="行政区划查询（面）：返回边界多边形WKT")
async def amap_district(
    keywords: str = Query(..., description="区划名称，如：安顺市、贵州省、西秀区"),
    level: str = Query("district", description="行政级别：province=省 / city=市 / district=区县"),
    user: User = Depends(current_user),
):
    """查某级行政区划的边界多边形（WGS84 WKT），不入库"""
    try:
        result = amap_client.get_district(keywords=keywords, level=level)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    return {"total": len(result), "items": result}


@router_amap.post("/district_import", summary="行政区划查询并导入面表（Polygon_feature）")
async def amap_district_import(
    keywords: str = Query(..., description="区划名称，如：安顺市、贵州省、西秀区"),
    level: str = Query("district", description="行政级别：province/city/district"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """查行政区划边界并写入面表（同名跳过，幂等）"""
    try:
        result = amap_client.get_district(keywords=keywords, level=level)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")

    inserted, skipped = 0, 0
    for d in result:
        if not d["wkt"]:
            skipped += 1  # 高德未返回边界数据
            continue
        # 幂等：同名边界已存在则跳过
        exists = await db.execute(select(PolygonFeature.id).where(
            PolygonFeature.name == f"{d['name']}边界",
            PolygonFeature.userid == user.userid,
        ))
        if exists.scalar_one_or_none():
            skipped += 1
            continue

        polygon = PolygonCreate(
            name=f"{d['name']}边界",
            address=f"adcode: {d['adcode']}",
            geom=d["wkt"],          # 已转 WGS84
            coord_sys=4326,
        )
        await create_polygon(db, polygon, user.userid)
        inserted += 1

    return {
        "fetched": len(result),
        "inserted": inserted,
        "skipped": skipped,
        "message": f"导入完成：新增 {inserted} 条，跳过 {skipped} 条",
    }


# ------------------------------
# 线数据：路径规划
# ------------------------------
@router_amap.get("/route", summary="驾车路径规划（线）：返回路线LINESTRING WKT")
async def amap_route(
    origin_lon: float = Query(..., description="起点经度(WGS84)"),
    origin_lat: float = Query(..., description="起点纬度(WGS84)"),
    dest_lon: float = Query(..., description="终点经度(WGS84)"),
    dest_lat: float = Query(..., description="终点纬度(WGS84)"),
    user: User = Depends(current_user),
):
    """两点间驾车路线（WGS84 WKT 折线 + 里程/耗时），不入库"""
    try:
        result = amap_client.route_driving(
            origin_lon=origin_lon, origin_lat=origin_lat,
            dest_lon=dest_lon, dest_lat=dest_lat,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    if not result.get("wkt"):
        raise HTTPException(status_code=502, detail=result.get("error", "路线获取失败"))
    return result


@router_amap.post("/route_import", summary="路径规划并导入线表（Linestring_feature）")
async def amap_route_import(
    origin_lon: float = Query(..., description="起点经度(WGS84)"),
    origin_lat: float = Query(..., description="起点纬度(WGS84)"),
    dest_lon: float = Query(..., description="终点经度(WGS84)"),
    dest_lat: float = Query(..., description="终点纬度(WGS84)"),
    route_name: str = Query("路线", description="路线名称，如：安顺学院→安顺站"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """两点间驾车路线写入线表（同名跳过，幂等）"""
    try:
        result = amap_client.route_driving(
            origin_lon=origin_lon, origin_lat=origin_lat,
            dest_lon=dest_lon, dest_lat=dest_lat,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"高德服务错误：{e}")
    if not result.get("wkt"):
        raise HTTPException(status_code=502, detail=result.get("error", "路线获取失败"))

    # 幂等：同名路线已存在则跳过
    exists = await db.execute(select(LinestringFeature.id).where(
        LinestringFeature.name == route_name,
        LinestringFeature.userid == user.userid,
    ))
    if exists.scalar_one_or_none():
        return {"message": f"路线 [{route_name}] 已存在，跳过导入", "inserted": 0}

    line = LinestringCreate(
        name=route_name,
        address=f"距离{result['distance_m']}m 约{int(result['duration_s']) // 60}分钟",
        geom=result["wkt"],
        coord_sys=4326,
    )
    await create_linestring(db, line, user.userid)
    return {
        "inserted": 1,
        "distance_m": result["distance_m"],
        "duration_s": result["duration_s"],
        "message": f"路线 [{route_name}] 已入库",
    }
