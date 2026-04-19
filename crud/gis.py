from fastapi import UploadFile
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func

from models import LinestringFeature,PolygonFeature
from crud import crud_LINESTRING,crud_POLYGON

async def test():
    pass

async def get_id_geometry(db: AsyncSession,table,tableid,userid: int):
    #根据id差要素
    result = await db.execute(select(table).
                        where(table.id == tableid, table.userid == userid))
    return result.scalar_one_or_none()

# ------------------------------
# GIS核心空间查询
# ------------------------------
async def get_nearby(db: AsyncSession, lon: float, lat: float, radius: float, table, userid: int):
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
    query = select(table).where(table.userid == userid,
                                func.ST_DWithin(
            func.ST_Transform(table.geom, 3857),
            func.ST_Transform(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), 3857),
            radius
        )
                                )
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
    bbox = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    query = select(table).where(table.userid==userid,func.ST_Intersects(table.geom, bbox))
    result = await db.execute(query)
    return result.scalars().all()

async def get_by_geometry(db: AsyncSession,table_1,table_2,userid: int,table1_id: int,):
    """要素相交查询"""
    #ST_Union将多个要素 union 成一个几何
    # scalar_subquery()感觉是为了代替db.execute，但是为了只执行一次，所以使用。一条 SQL 里直接嵌套子查询
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
                            )
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

async def geometry_in_geometry(db: AsyncSession,table_1,table_2,userid: int,table1_id: int):
    """要素包含查询"""
    # ST_Within (几何 A, 几何 B)  A 的全部 是否 完全在 B 内部
    #拿到 面(多边形) 的 geom
    verify = await get_id_geometry(db=db,table=table_1,tableid=table1_id,userid=userid)
    if not verify:
        return None
    if table1_id:
        subquery = (
            select(table_1.geom)
            .where(table_1.id == table1_id,table_1.userid == userid)
        ).scalar_subquery()# 把 “一行数据 / 查询集” → 扒成 “一个单独的值”...这里变成纯 geom 值

    else:
        subquery = (
            select(func.ST_Union(table_1.geom))
            .where(table_1.userid == userid)
        ).scalar_subquery() # 把 “一行数据 / 查询集” → 扒成 “一个单独的值”...这里变成纯 geom 值
   # 找出所有在这个面内的要素
    query = (
        select(table_2)
        .where(
            # PostGIS 核心判断：要素 是否 在 面 内
            func.ST_Within(table_2.geom, subquery),
            table_2.userid == userid
        )
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

async def import_file_point(db: AsyncSession, file: UploadFile, userid: int):
    """导入Excel文件数据"""
    # 检查文件类型,endswith判断一个字符串结尾,多个参数必须填元组
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', 'csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
        # 读取文件内容
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))

        # 检查必要列
        required_columns = ['name', 'address', 'lon', 'lat']
        for col in required_columns:
            if col not in df.columns:#获取这个 Excel 表格的 所有列名
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        # 转换数据
        data_list = df.to_dict(orient="records")
        i = 0
        list_exception = []
        # 批量添加数据
        for start,item in enumerate(data_list,start=1):
            lon = item["lon"]
            lat = item['lat']
            if not lon or not lat or not (-180 <= lon <= 180 and -90 <= lat <= 90):
                i+=1
                list_exception.append(start)
                continue

            point = PointFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                geom=f"SRID=4326;POINT({lon} {lat})"
            )
            db.add(point)

        await db.commit()
        return {"success": True, "imported": len(data_list),"skipped":i,"Abnormal location":list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")


async def import_file_linestring(db: AsyncSession, file: UploadFile, userid: int):
    """导入Excel文件数据"""
    # 检查文件类型,endswith判断一个字符串结尾,多个参数必须填元组
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', 'csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            # 读取文件内容
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))

        # 检查必要列
        required_columns = ['name', 'address', "coordinates"]
        for col in required_columns:
            if col not in df.columns:#获取这个 Excel 表格的 所有列名
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        # 转换数据
        data_list = df.to_dict(orient="records")
        i=0
        list_exception = []
        # 批量添加数据
        for start,item in enumerate(data_list,start=1):
            # 从 Excel 获取坐标字符串，例如：116.3,39.5;116.4,39.6
            coords_str = item["coordinates"].strip()
            if not coords_str:
                i+=1
                list_exception.append(start)
                continue

            # 创建线要素
            line = LinestringFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                geom=f"SRID=4326;LINESTRING({coords_str})"
            )
            db.add(line)

        await db.commit()
        return {"success": True, "imported": len(data_list),"skipped":i,"Abnormal location":list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")


async def import_file_polygon(db: AsyncSession, file: UploadFile, userid: int):
    filename = file.filename.lower()
    if not filename.endswith(('.xlsx', '.xls', 'csv')):
        raise ValueError("文件后缀为 .xlsx, .xls, .csv")
    contents = await file.read()
    try:
        if filename.endswith(('.xlsx', '.xls')):
            # 读取文件内容
            df = pandas.read_excel(io.BytesIO(contents))
        else:
            df = pandas.read_csv(io.BytesIO(contents))
        # 检查必要列
        required_columns = ['name', 'address', "coordinates"]
        for col in required_columns:
            if col not in df.columns:#获取这个 Excel 表格的 所有列名
                raise ValueError(f"Excel 文件缺少必要列: {col}")

        # 转换数据
        data_list = df.to_dict(orient="records")
        i = 0
        list_exception = []
        # 批量添加数据
        for start,item in enumerate(data_list,start=1):
            # 从 Excel 获取坐标
            coords_str = item["coordinates"].strip()
            #消除空格
            coord_list = coords_str.split(",")
            coord_list_strip = [c.strip() for c in coord_list]

            if not coords_str or coord_list_strip[0] != coord_list_strip[-1]:
                i+= 1
                list_exception.append(start)
                continue

            # 3. 创建面模型
            polygon = PolygonFeature(
                name=str(item["name"]),
                address=str(item["address"]),
                userid=int(userid),
                geom=f"SRID=4326;POLYGON(({coords_str}))"
            )
            db.add(polygon)

        await db.commit()
        return {"success": True, "imported": len(data_list),"skipped":i,"Abnormal location":list_exception}

    except Exception as e:
        await db.rollback()
        raise ValueError(f"导入失败: {str(e)}")












