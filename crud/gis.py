from fastapi import UploadFile
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func

from models import LinestringFeature, PolygonFeature, PointFeature
from crud import crud_LINESTRING, crud_POLYGON
import pandas
import io

# ------------------------------
# 数据统计
# ------------------------------

async def get_summary(db: AsyncSession, userid: int) -> dict:
    """统计当前用户各图层要素数量"""
    models = {
        "point": PointFeature,
        "linestring": LinestringFeature,
        "polygon": PolygonFeature,
    }
    result = {}
    total = 0
    for key, model in models.items():
        count_result = await db.execute(
            select(func.count(model.id)).where(model.userid == userid)
        )
        count = count_result.scalar()
        result[key] = count
        total += count
    result["total"] = total
    return result


# ------------------------------
# 导出
# ------------------------------
async def validate_srid(db: AsyncSession, srid: int) -> bool:
    """
    校验 SRID 是否在 PostGIS 的 spatial_ref_sys 表中存在。
    :param db: 数据库会话
    :param srid: 要校验的 SRID
    :return: True 存在，False 不存在
    """
    from sqlalchemy import text
    row = await db.execute(
        text("SELECT COUNT(*) FROM spatial_ref_sys WHERE srid = :srid"),
        {"srid": srid}
    )
    return row.scalar() > 0


def transform_geom_col(model, target_srid: int):
    """
    返回 SQLAlchemy 列表达式，用于在 SQL 中对 geom 列做坐标转换。
    ST_Transform 会自动从 geom 读取源 SRID。
    :param model: ORM 模型（PointFeature / LinestringFeature / PolygonFeature）
    :param target_srid: 目标坐标系 SRID
    :return: SQLAlchemy 列表达式，可直接用于 select()
    """
    return func.ST_Transform(model.geom, target_srid).label('geom')


async def transform_features(
    db: AsyncSession,
    model,
    target_srid: int,
    userid: int = None,
    feature_ids: list[int] = None,
    page: int = 1,
    page_size: int = 6
):
    """
    独立的坐标转换查询函数。
    根据目标 SRID 对数据库中的要素进行坐标转换后返回。
    ST_Transform 会自动从 geom 读取源 SRID。

    :param db: 数据库会话
    :param model: ORM 模型（PointFeature / LinestringFeature / PolygonFeature）
    :param target_srid: 目标坐标系 SRID（如 3857、4490）
    :param userid: 用户 ID（可选，用于过滤）
    :param feature_ids: 指定要素 ID 列表（可选，不传则查询全部）
    :param page: 页码（默认 1）
    :param page_size: 每页数量（默认 6）
    :return: 转换后的要素列表
    """
    geom_col = transform_geom_col(model, target_srid)
    stmt = (
        select(
            model.id, model.userid, model.name, model.address,
            model.coord_sys, model.create_time, model.update_time, geom_col
        )
    )

    if userid is not None:
        stmt = stmt.where(model.userid == userid)
    if feature_ids:
        stmt = stmt.where(model.id.in_(feature_ids))

    skip = (page - 1) * page_size
    stmt = stmt.order_by(model.id).offset(skip).limit(page_size)

    result = await db.execute(stmt)
    rows = result.all()

    features = []
    for row in rows:
        obj = model()
        for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
            setattr(obj, col, getattr(row, col))
        features.append(obj)

    return features

async def get_id_geometry(db: AsyncSession,table,tableid,userid: int):
    result = await db.execute(select(table).
                        where(table.id == tableid, table.userid == userid))
    return result.scalar_one_or_none()

# ------------------------------
# GIS核心空间查询
# ------------------------------
async def get_nearby(db: AsyncSession, lon: float, lat: float, radius: float, table, userid: int,page: int):
    """
    附近点位查询（GIS核心功能）
    :param lon: 中心点经度
    :param lat: 中心点纬度
    :param radius: 查询半径（米）
    """
    # ST_DWithin：判断两个几何是否在指定距离内
    # ST_Transform：坐标转换，4326转3857（墨卡托投影，单位米）
    #ST_MakePoint：生成空间点数据
    #ST_SetSRID： 给这个点设置坐标系
    stmt = (page-1)*6

    query = select(table).where(table.userid == userid,
                                func.ST_DWithin(
            func.ST_Transform(table.geom, 3857),
            func.ST_Transform(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), 3857),
            radius
        )
     ).order_by(table.id).offset(stmt).limit(6)
    result = await db.execute(query)
    return result.scalars().all()

async def get_by_bbox(
    db: AsyncSession,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    table,
    userid: int,
    page: int
):
    """
    矩形范围查询（bbox查询，地图常用）
    :param min_lon: 最小经度
    :param min_lat: 最小纬度
    :param max_lon: 最大经度
    :param max_lat: 最大纬度
    """
    # ST_MakeEnvelope：创建矩形范围
    # ST_Intersects：判断两个几何是否相交

    stmt = (page - 1) * 6

    bbox = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    query = (select(table)
             .where(table.userid==userid,func.ST_Intersects(table.geom, bbox))
             .order_by(table.id).offset(stmt).limit(6))
    result = await db.execute(query)
    return result.scalars().all()

async def get_by_geometry(db: AsyncSession,table_1,table_2,userid: int,table1_id: int,page: int):
    """要素相交查询"""
    #ST_Union将多个要素 union 成一个几何
    # scalar_subquery()感觉是为了代替db.execute，但是为了只执行一次，所以使用。一条 SQL 里直接嵌套子查询

    stmt = (page - 1) * 6

    if table1_id:
    #查询单一要素
        subquery = (select(table_1.geom)
                        .where(table_1.userid == userid,table_1.id==table1_id)
                        ).scalar_subquery()
    #查询所有
    else:
        subquery = (select(func.ST_Union(table_1.geom))
                    .where(table_1.userid == userid)
                    ).scalar_subquery()

    query_all = ((select(table_2))
                 .where(table_2.userid == userid
                        , func.ST_Intersects(table_2.geom, subquery)
                            ).order_by(table_2.id).offset(stmt).limit(6)
                     )


    result = await db.execute(query_all)
    return result.scalars().all()


async def get_geometry_geometry(db: AsyncSession,userid: int,id_1: int,id_2: int,table_1,table_2):
    """要素距离计算 / 要素到要素的最近点投影...查询谁，谁就在前面"""
    #ST_DistanceSphere 计算两个几何图形之间的最短距离,返回m
    #ST_ClosestPoint找到 B 图形上，离 A 图形最近的那个点。
    #ST_AsText()函数，并且只接受 "一个" 值  转为WKT

    verify_1 = await get_id_geometry(db=db,table=table_1,tableid=id_1,userid=userid)
    verify_2 = await get_id_geometry(db=db, table=table_2,tableid=id_2,userid=userid)
    if not verify_1 or not verify_2:
        return None

    query = (
        select(
            func.ST_DistanceSphere(table_1.geom, table_2.geom).label("distance"),

            func.ST_ClosestPoint(table_1.geom, table_2.geom).label("closest_point")
        )
        .where(
            table_1.id == id_1 ,
            table_2.id == id_2,
            table_1.userid == userid,
            table_2.userid == userid
        )
    )

    result = await db.execute(query)
    row = result.fetchone()

    if not row:
        return 0.0, None  # 必须返回两个值

    return row.distance, mapping(to_shape(row.closest_point))

async def geometry_in_geometry(db: AsyncSession,table_1,table_2,userid: int,table1_id: int,page: int):
    """要素包含查询"""
    # ST_Within (几何 A, 几何 B)  A 的全部 是否 完全在 B 内部
    #拿到 面(多边形) 的 geom

    stmt = (page - 1) * 6

    verify = await get_id_geometry(db=db,table=table_1,tableid=table1_id,userid=userid)
    if not verify:
        return None
    if table1_id:
        subquery = (
            select(table_1.geom)
            .where(table_1.id == table1_id,table_1.userid == userid)
        ).scalar_subquery()

    else:
        subquery = (
            select(func.ST_Union(table_1.geom))
            .where(table_1.userid == userid)
        ).scalar_subquery()
   # 找出所有在这个面内的要素
    query = (
        select(table_2)
        .where(
            # PostGIS 核心判断：要素 是否 在 面 内
            func.ST_Within(table_2.geom, subquery),
            table_2.userid == userid
        ).order_by(table_2.id).offset(stmt).limit(6)
    )
    # 执行查询
    result = await db.execute(query)
    points = result.scalars().all()
    return points


async def get_linestring_length(db: AsyncSession, linestring_id: int,userid: int):
    """计算长度"""
    result  = await crud_LINESTRING.get_linestring_by_id(db=db, linestring_id=linestring_id, userid=userid)
    if result:
        result = await db.execute(select(
                func.ST_Length(LinestringFeature.geom, True)#True = 计算真实地理长度
            .label("length"))
            .where(LinestringFeature.id == linestring_id))

        data = result.first()
        return data.length
    return None

async def get_polygon_area(db: AsyncSession, polygon_id: int,userid: int):
    """计算面积"""
    rsult = crud_POLYGON.get_polygon_by_id(db=db, polygon_id=polygon_id,userid=userid)
    if rsult:
        result = await db.execute(select(
            func.ST_Area(PolygonFeature.geom, True)
        .label("area_meter"))
        .where(PolygonFeature.id == polygon_id))

        area = result.scalar()
        return area
    return None

from models import PointFeature
import pandas
import io

async def export_features(
    db: AsyncSession,
    model,
    userid: int,
    target_srid: int = None,
    feature_ids: list[int] = None,
):
    """
    导出要素数据，无分页，支持坐标系转换。
    返回 model 对象列表，可直接调用 to_geojson_feature()。
    """
    if target_srid is not None:
        geom_col = func.ST_Transform(model.geom, target_srid).label('geom')
    else:
        geom_col = model.geom

    stmt = select(
        model.id, model.userid, model.name, model.address,
        model.coord_sys, model.create_time, model.update_time, geom_col
    ).where(model.userid == userid)

    if feature_ids:
        stmt = stmt.where(model.id.in_(feature_ids))

    stmt = stmt.order_by(model.id)

    result = await db.execute(stmt)
    rows = result.all()

    features = []
    for row in rows:
        obj = model()
        for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
            setattr(obj, col, getattr(row, col))
        features.append(obj)

    return features


async def import_file_point(db: AsyncSession, file: UploadFile, userid: int):
    """导入Excel文件数据"""
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', '.csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))

        # 检查必要列
        required_columns = ['name', 'address', 'lon', 'lat']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        has_coord_sys = 'coord_sys' in df.columns

        # 转换数据
        data_list = df.to_dict(orient="records")
        i = 0
        list_exception = []
        # 批量添加数据
        for start, item in enumerate(data_list, start=1):
            lon = item["lon"]
            lat = item['lat']
            coord_sys = int(item.get('coord_sys', 4326)) if has_coord_sys else 4326

            # 4326/4490 地理坐标系才校验经纬度范围
            if coord_sys in (4326, 4490):
                if not lon or not lat or not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    i += 1
                    list_exception.append(start)
                    continue

            point = PointFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                coord_sys=coord_sys,
                geom=f"SRID={coord_sys};POINT({lon} {lat})"
            )

            db.add(point)

        await db.commit()
        return {"success": True, "imported": len(data_list), "skipped": i, "Abnormal location": list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")


async def import_file_linestring(db: AsyncSession, file: UploadFile, userid: int):
    """导入Excel文件数据"""
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', '.csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))

        # 检查必要列
        required_columns = ['name', 'address', "coordinates"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        has_coord_sys = 'coord_sys' in df.columns

        # 转换数据
        data_list = df.to_dict(orient="records")
        i = 0
        list_exception = []
        # 批量添加数据
        for start, item in enumerate(data_list, start=1):
            coords_str = item["coordinates"].strip()
            if not coords_str:
                i += 1
                list_exception.append(start)
                continue

            coord_sys = int(item.get('coord_sys', 4326)) if has_coord_sys else 4326

            line = LinestringFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                coord_sys=coord_sys,
                geom=f"SRID={coord_sys};LINESTRING({coords_str})"
            )

            db.add(line)

        await db.commit()
        return {"success": True, "imported": len(data_list), "skipped": i, "Abnormal location": list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")


async def import_file_polygon(db: AsyncSession, file: UploadFile, userid: int):
    """导入Excel文件数据"""
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', '.csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))
        # 检查必要列
        required_columns = ['name', 'address', "coordinates"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        has_coord_sys = 'coord_sys' in df.columns

        # 转换数据
        data_list = df.to_dict(orient="records")
        i = 0
        list_exception = []
        # 批量添加数据
        for start, item in enumerate(data_list, start=1):
            coords_str = item["coordinates"].strip()
            coord_list = coords_str.split(",")
            coord_list_strip = [c.strip() for c in coord_list]

            if not coords_str or coord_list_strip[0] != coord_list_strip[-1]:
                i += 1
                list_exception.append(start)
                continue

            coord_sys = int(item.get('coord_sys', 4326)) if has_coord_sys else 4326

            polygon = PolygonFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                coord_sys=coord_sys,
                geom=f"SRID={coord_sys};POLYGON(({coords_str}))"
            )

            db.add(polygon)

        await db.commit()
        return {"success": True, "imported": len(data_list), "skipped": i, "Abnormal location": list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")


async def import_geojson(db: AsyncSession, file: UploadFile, userid: int, coord_sys: int = 4326):
    """
    从 GeoJSON 文件导入要素，自动识别 Point / LineString / Polygon。
    支持 FeatureCollection 和单条 Feature。
    """
    import json

    filename = file.filename.lower()
    if not filename.endswith(('.geojson', '.json')):
        raise ValueError("文件后缀需为 .geojson 或 .json")

    contents = await file.read()
    try:
        data = json.loads(contents.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("文件不是有效的 JSON/GeoJSON 格式")

    # 统一转为 features 列表
    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif data.get("type") == "Feature":
        features = [data]
    else:
        raise ValueError("GeoJSON 格式不正确，需要 FeatureCollection 或 Feature")

    if not features:
        raise ValueError("GeoJSON 文件中没有要素")

    geom_type_map = {
        "Point": PointFeature,
        "MultiPoint": PointFeature,
        "LineString": LinestringFeature,
        "MultiLineString": LinestringFeature,
        "Polygon": PolygonFeature,
        "MultiPolygon": PolygonFeature,
    }

    imported = 0
    skipped = 0
    for i, feature in enumerate(features, start=1):
        geometry = feature.get("geometry")
        if not geometry:
            skipped += 1
            continue

        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")
        if not geom_type or not coords:
            skipped += 1
            continue

        model = geom_type_map.get(geom_type)
        if not model:
            skipped += 1
            continue

        props = feature.get("properties", {}) or {}
        name = str(props.get("name", f"导入要素_{i}"))
        address = str(props.get("address") or "")

        # 坐标 → WKT
        wkt = coords_to_wkt(geom_type, coords)

        obj = model(
            name=name,
            address=address if address else None,
            userid=userid,
            coord_sys=coord_sys,
            geom=f"SRID={coord_sys};{wkt}",
        )
        db.add(obj)
        imported += 1

    await db.commit()
    return {"success": True, "imported": imported, "skipped": skipped}


def coords_to_wkt(geom_type: str, coords) -> str:
    """将 GeoJSON 坐标数组转为 WKT 字符串"""
    if geom_type == "Point":
        return f"POINT({coords[0]} {coords[1]})"

    if geom_type == "MultiPoint":
        pts = ", ".join(f"{c[0]} {c[1]}" for c in coords)
        return f"MULTIPOINT({pts})"

    if geom_type == "LineString":
        pts = ", ".join(f"{c[0]} {c[1]}" for c in coords)
        return f"LINESTRING({pts})"

    if geom_type == "MultiLineString":
        lines = ", ".join(
            "(" + ", ".join(f"{c[0]} {c[1]}" for c in line) + ")"
            for line in coords
        )
        return f"MULTILINESTRING({lines})"

    if geom_type == "Polygon":
        rings = ", ".join(
            "(" + ", ".join(f"{c[0]} {c[1]}" for c in ring) + ")"
            for ring in coords
        )
        return f"POLYGON({rings})"

    if geom_type == "MultiPolygon":
        polys = ", ".join(
            "(" + ", ".join(
                "(" + ", ".join(f"{c[0]} {c[1]}" for c in ring) + ")"
                for ring in poly
            ) + ")"
            for poly in coords
        )
        return f"MULTIPOLYGON({polys})"

    raise ValueError(f"不支持的几何类型: {geom_type}")


async def import_shapefile(db: AsyncSession, file: UploadFile, userid: int, coord_sys: int = 4326):
    """
    从 Shapefile (.zip) 导入要素。
    zip 内需包含 .shp / .shx / .dbf，自动识别点/线/面。
    """
    import tempfile
    import zipfile
    import os
    import shapefile

    filename = file.filename.lower()
    if not filename.endswith('.zip'):
        raise ValueError("Shapefile 需打包为 .zip 上传，内包含 .shp / .shx / .dbf")

    contents = await file.read()

    # 解压到临时目录
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            zf.extractall(tmpdir)

        # 找 .shp 文件
        shp_files = [f for f in os.listdir(tmpdir) if f.lower().endswith('.shp')]
        if not shp_files:
            raise ValueError("zip 中未找到 .shp 文件")
        shp_path = os.path.join(tmpdir, shp_files[0])

        sf = shapefile.Reader(shp_path)

        geom_type_map = {
            shapefile.POINT:        ("Point", PointFeature),
            shapefile.POINTZ:       ("Point", PointFeature),
            shapefile.POINTM:       ("Point", PointFeature),
            shapefile.MULTIPOINT:   ("MultiPoint", PointFeature),
            shapefile.MULTIPOINTZ:  ("MultiPoint", PointFeature),
            shapefile.MULTIPOINTM:  ("MultiPoint", PointFeature),
            shapefile.POLYLINE:     ("LineString", LinestringFeature),
            shapefile.POLYLINEZ:    ("LineString", LinestringFeature),
            shapefile.POLYLINEM:    ("LineString", LinestringFeature),
            shapefile.POLYGON:      ("Polygon", PolygonFeature),
            shapefile.POLYGONZ:     ("Polygon", PolygonFeature),
            shapefile.POLYGONM:     ("Polygon", PolygonFeature),
        }

        imported = 0
        skipped = 0
        field_names = [f[0] for f in sf.fields[1:]]  # 跳过 DeletionFlag

        for sr in sf.iterShapeRecords():
            shape_type = sr.shape.shapeType
            mapping = geom_type_map.get(shape_type)
            if not mapping:
                skipped += 1
                continue

            wkt_type, model = mapping
            wkt = shape_to_wkt(wkt_type, sr.shape)

            record = dict(zip(field_names, sr.record))
            name = str(record.get("name", record.get("NAME", record.get("Name", f"导入要素_{imported + 1}"))))
            address = str(record.get("address", record.get("address", record.get("ADDRESS", ""))))

            obj = model(
                name=name,
                address=address if address else None,
                userid=userid,
                coord_sys=coord_sys,
                geom=f"SRID={coord_sys};{wkt}",
            )
            db.add(obj)
            imported += 1

        await db.commit()

    return {"success": True, "imported": imported, "skipped": skipped}


def shape_to_wkt(wkt_type: str, shape) -> str:
    """将 pyshp Shape 对象转为 WKT 字符串"""
    pts = shape.points

    if wkt_type in ("Point",):
        return f"POINT({pts[0][0]} {pts[0][1]})"

    if wkt_type in ("MultiPoint",):
        coords = ", ".join(f"{p[0]} {p[1]}" for p in pts)
        return f"MULTIPOINT({coords})"

    if wkt_type in ("LineString",):
        # pyshp: parts 列表标记每条线的起始点索引
        lines = []
        parts = list(shape.parts) + [len(pts)]
        for i in range(len(parts) - 1):
            segment = pts[parts[i]:parts[i + 1]]
            lines.append("(" + ", ".join(f"{p[0]} {p[1]}" for p in segment) + ")")
        if len(lines) == 1:
            return f"LINESTRING({lines[0][1:-1]})"
        return f"MULTILINESTRING({', '.join(lines)})"

    if wkt_type in ("Polygon",):
        rings = []
        parts = list(shape.parts) + [len(pts)]
        for i in range(len(parts) - 1):
            ring = pts[parts[i]:parts[i + 1]]
            rings.append("(" + ", ".join(f"{p[0]} {p[1]}" for p in ring) + ")")
        if len(rings) == 1:
            return f"POLYGON({rings[0]})"
        return f"MULTIPOLYGON(({'), ('.join(rings)}))"

    raise ValueError(f"不支持的 WKT 类型: {wkt_type}")

