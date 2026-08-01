"""
高德开放平台 Web 服务 API 客户端
官方文档：https://lbs.amap.com/api/webservice/summary

⚠️ 坐标系说明（GIS 必修课）：
    高德返回的坐标是 GCJ-02（火星坐标系，国家加密偏移坐标系），
    与项目使用的 WGS84(4326) 存在约几十到几百米的偏差，
    入库前必须调用 gcj02_to_wgs84() 转换，否则空间分析结果全错。
"""
import json
import math
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import settings

AMAP_BASE = "https://restapi.amap.com/v3"


# ============================================================
# 坐标系转换：GCJ-02 → WGS84（公开的纠偏算法，精度约几米，学习够用）
# ============================================================
def _out_of_china(lon: float, lat: float) -> bool:
    """判断是否在中国境外（境外无偏移，无需转换）"""
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(lon: float, lat: float) -> float:
    ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320.0 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(lon: float, lat: float) -> float:
    ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * math.sqrt(abs(lon))
    ret += (20.0 * math.sin(6.0 * lon * math.pi) + 20.0 * math.sin(2.0 * lon * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lon * math.pi) + 40.0 * math.sin(lon / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lon / 12.0 * math.pi) + 300.0 * math.sin(lon / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    """火星坐标 → WGS84 经纬度"""
    if _out_of_china(lon, lat):
        return lon, lat

    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - 0.00669342162296594323 * magic * magic  # 地球椭球偏心率相关常数
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
    return lon - dlon, lat - dlat


def wgs84_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    """WGS84 经纬度 → 火星坐标（逆地理编码等需要，高德接口只收 GCJ-02）"""
    if _out_of_china(lon, lat):
        return lon, lat

    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (6378245.0 / sqrtmagic * math.cos(radlat) * math.pi)
    return lon + dlon, lat + dlat


# ============================================================
# API 封装
# ============================================================
def _request(params: dict, path: str = "/place/text") -> dict:
    """发 GET 请求并解析响应，公共参数自动带上 Key"""
    params["key"] = settings.AMAP_KEY
    url = f"{AMAP_BASE}{path}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "GeoAPI_Lite/1.0"})
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("status") != "1":
        raise RuntimeError(f"高德 API 错误：{data.get('info')}（infocode: {data.get('infocode')}）")
    return data


def search_poi(keywords: str, city: str = None, page: int = 1, offset: int = 25,
               types: str = None, sleep: float = 0.35) -> dict:
    """
    关键词 POI 文本搜索（/place/text）

    参数：
        keywords: 搜索关键词，如 "学校"、"医院"
        city: 城市名或 adcode，如 "安顺市"（不传则全国搜索）
        page / offset: 分页，单页最多 25 条
        types: 高德 POI 类型码（如 141100 大学、141200 中学），不传则按关键词搜
        sleep: 请求间隔秒数（免费 Key 有 QPS 限制，默认约 3 QPS 保险值）

    返回：{"count": 总数, "pois": [{"name","location","address","type","typecode",
                                    "pname","cityname","adname"}, ...]}
    """
    params = {
        "page": page,
        "offset": offset,
        "extensions": "base",
    }
    # 注意：urlencode 会把 None 编码成字符串 "None"，所以 None 参数必须跳过
    if keywords:
        params["keywords"] = keywords
    if city:
        params["city"] = city
    if types:
        params["types"] = types

    data = _request(params)

    pois = []
    for item in data.get("pois", []):
        lon_str, lat_str = item["location"].split(",")
        pois.append({
            "name": item.get("name", ""),
            "lon": float(lon_str),            # 注意：这是 GCJ-02 坐标
            "lat": float(lat_str),
            "address": item.get("address", ""),
            "type": item.get("type", ""),
            "typecode": item.get("typecode", ""),
            "province": item.get("pname", ""),
            "city": item.get("cityname", ""),
            "district": item.get("adname", ""),
        })
    if sleep:
        time.sleep(sleep)  # 控制 QPS，避免被限流
    return {"count": int(data.get("count", 0)), "pois": pois}


def search_poi_many(keywords: str = None, city: str = None, pages: int = 1, offset: int = 25,
                    types: str = None) -> list[dict]:
    """
    分页抓取 POI 并自动去重（高德分页在 POI 数超过 offset 时会出现偏移重复）

    参数：
        keywords: 关键词（按名称搜），与 types 二选一
        types: 高德 POI 类型码，如 1412=学校大类、050000=风景名胜、060100=餐饮
        city: 城市名或 adcode，如 "安顺市" / "520400"（实测 adcode 更稳定）

    返回：去重后的 POI 列表（坐标已转为 WGS84）
    """
    seen = set()
    results = []
    for page in range(1, pages + 1):
        data = search_poi(keywords=keywords, city=city, page=page, offset=offset, types=types)
        if not data["pois"]:
            break
        for poi in data["pois"]:
            key = (poi["name"], poi["lon"], poi["lat"])
            if key in seen:
                continue
            seen.add(key)
            # 高德 GCJ-02 → 项目 WGS84
            poi["lon"], poi["lat"] = gcj02_to_wgs84(poi["lon"], poi["lat"])
            results.append(poi)
    return results


def geocode(address: str, city: str = None) -> list[dict]:
    """
    地理编码：地址文本 → 经纬度（/geocode/geo）
    返回坐标已转为 WGS84，与项目坐标系一致
    """
    params = {"address": address}
    if city:
        params["city"] = city
    data = _request(params, path="/geocode/geo")

    results = []
    for g in data.get("geocodes", []):
        if not g.get("location"):
            continue
        lon, lat = map(float, g["location"].split(","))
        lon, lat = gcj02_to_wgs84(lon, lat)
        results.append({
            "formatted_address": g.get("formatted_address", ""),
            "lon": lon,
            "lat": lat,
            "adcode": g.get("adcode", ""),
            "level": g.get("level", ""),
        })
    return results


def regeo(lon: float, lat: float) -> dict:
    """
    逆地理编码：经纬度 → 地址（/geocode/regeo）
    输入为 WGS84（项目标准），内部转成 GCJ-02 再请求高德
    """
    gcj_lon, gcj_lat = wgs84_to_gcj02(lon, lat)
    data = _request({"location": f"{gcj_lon},{gcj_lat}"}, path="/geocode/regeo")

    rg = data.get("regeocode", {})
    ac = rg.get("addressComponent", {})
    return {
        "formatted_address": rg.get("formatted_address", ""),
        "province": ac.get("province", ""),
        "city": ac.get("city", ""),
        "district": ac.get("district", ""),
        "adcode": ac.get("adcode", ""),
    }


def get_district(keywords: str, level: str = "district", subdistrict: int = 0) -> list[dict]:
    """
    行政区划查询（/config/district）：返回行政区域的边界多边形（面数据）
    extensions=all 才会返回边界 polyline；GCJ-02 已转 WGS84
    """
    data = _request({
        "keywords": keywords,
        "subdistrict": subdistrict,
        "extensions": "all",
        "level": level,
    }, path="/config/district")

    result = []
    for d in data.get("districts", []):
        polyline = d.get("polyline", "")
        result.append({
            "name": d.get("name", ""),
            "adcode": d.get("adcode", ""),
            "level": d.get("level", ""),
            "center": d.get("center", ""),          # GCJ-02 中心点
            "wkt": _polyline_to_wkt(polyline) if polyline else None,  # WGS84 多边形WKT
        })
    return result


def _polyline_to_wkt(polyline: str) -> str:
    """
    高德边界字符串 → PostGIS POLYGON WKT
    高德格式：多个面用 | 分隔，环内顶点用 ; 分隔，坐标 GCJ-02
    注：多面区划（如带岛屿）取顶点最多的环，简化入库（教学项目够用）
    """
    rings = []
    for ring_str in polyline.split("|"):
        coords = []
        for pt in ring_str.split(";"):
            lon, lat = map(float, pt.split(","))
            lon, lat = gcj02_to_wgs84(lon, lat)
            coords.append(f"{lon:.6f} {lat:.6f}")
        if not coords:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])  # 边界线可能不闭合，补闭合
        rings.append(coords)

    if not rings:
        return None
    # 取顶点最多的环（主区域）
    main_ring = max(rings, key=len)
    return "POLYGON((" + ", ".join(main_ring) + "))"


def route_driving(origin_lon: float, origin_lat: float, dest_lon: float, dest_lat: float,
                  strategy: int = 0) -> dict:
    """
    驾车路径规划（/direction/driving）：返回整条路线的 LINESTRING WKT（线数据）
    入参为 WGS84（项目标准），内部转 GCJ-02 请求高德
    """
    olon, olat = wgs84_to_gcj02(origin_lon, origin_lat)
    dlon, dlat = wgs84_to_gcj02(dest_lon, dest_lat)
    data = _request({
        "origin": f"{olon},{olat}",
        "destination": f"{dlon},{dlat}",
        "strategy": strategy,
        "extensions": "base",
    }, path="/direction/driving")

    paths = data.get("route", {}).get("paths", [])
    if not paths:
        return {"error": "高德未返回路线", "wkt": None}

    path = paths[0]
    points = []
    for step in path.get("steps", []):
        for pair in step.get("polyline", "").split(";"):
            if not pair:
                continue
            lon, lat = map(float, pair.split(","))
            lon, lat = gcj02_to_wgs84(lon, lat)
            points.append(f"{lon:.6f} {lat:.6f}")

    return {
        "wkt": "LINESTRING(" + ", ".join(points) + ")" if points else None,
        "distance_m": path.get("distance"),   # 总里程（米）
        "duration_s": path.get("duration"),   # 预计耗时（秒）
        "steps": len(path.get("steps", [])),
    }


if __name__ == "__main__":
    """自测：POI搜索 + 地理编码 + 逆地理编码"""
    demo = search_poi_many(types="1412", city="520400", pages=1)
    print(f"[POI搜索] 共抓取 {len(demo)} 条，前 3 条：")
    for p in demo[:3]:
        print(f"  {p['name']}  ({p['lon']:.6f}, {p['lat']:.6f})  {p['address']}")

    print("[地理编码] 安顺学院：")
    for g in geocode("安顺学院", city="安顺市"):
        print(f"  {g['formatted_address']}  ({g['lon']:.6f}, {g['lat']:.6f})")

    print("[逆地理编码] (105.94, 26.25)：")
    print(f"  {regeo(105.94, 26.25)}")
