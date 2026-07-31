import io
import json

import pandas
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database import get_db
from schemas import schemas_POINT,schemas_LINESTRING,schemas_POLYGON,schemas_GIS,schemas_USER
from crud import crud_POINT, crud_LINESTRING, crud_POLYGON, gis, crud_user, crud_token
from crud.gis import transform_features, validate_srid
from models import PointFeature, LinestringFeature, PolygonFeature, User
from utils.auth import current_user
from utils.geojson import to_feature_collection
from utils.mapping_table import LayerName,LAYER_MODEL_MAP,CoordSys
# 路由实例
router_user = APIRouter(prefix="/user", tags=["user"])

router_point = APIRouter(prefix="/api/point", tags=["Point"])
router_linestring = APIRouter(prefix='/api/linestring', tags=["Linestring"])
router_polygon = APIRouter(prefix='/api/polygon', tags=["Polygon"])
router_gis = APIRouter(prefix='/api/gis', tags=["Geo"])


# ------------------------------
# 用户接口
# ------------------------------

@router_user.post("/register",summary="创建用户")
async def create_user(user_data: schemas_USER.UserCreate,db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user_username(db=db,username=user_data.name)
    if user:
        raise HTTPException(status_code=400,detail="用户名已存在")
    user_data = await crud_user.create_user(db=db,user_data=user_data)
    return {"message": "用户创建成功", "user_id": user_data.userid}

@router_user.post("/login",summary="验证用户登录")
async def login_user(account: int|str, password: str, db: AsyncSession = Depends(get_db)):
    user = await crud_token.authenticate_user(db=db,account=account,password=password)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="用户名或密码错误")
    token = await crud_token.create_token(db=db,user_id=user.userid)
    return {"access_token": token, "token_type": "bearer", "user_id": user.userid}

@router_user.put("/update",summary="修改用户信息",response_model=schemas_USER.UserDetail)
async def update_user(
        update: schemas_USER.UserUpdate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    # 只有当用户名改变时，才检查是否重复
    if update.name and update.name != user.name:
        existing_user = await crud_user.get_user_username(db=db, username=update.name)
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
    
    upuser = await crud_user.put_update_user(db=db, userid=user.userid, user_data=update)
    return upuser

@router_user.put("/password",summary="修改密码")
async def update_password(
        old_password: str = Query(..., description="旧密码"),
        new_password: str = Query(..., description="新密码"),
        db: AsyncSession=Depends(get_db),
        user: User = Depends(current_user)
):
    c = await crud_user.update_password(db=db,user=user,old_password=old_password,new_password=new_password)
    if not c:
        raise HTTPException(status_code=400,detail="密码错误")
    return {"massage":"ok"}



@router_gis.get("/info",summary="测试接口")
async def get_test(db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    pass
# ------------------------------
# 基础CRUD接口
# ------------------------------
@router_point.post("/", summary="创建点位", response_model=schemas_POINT.PointDetail)
async def create_point(
    point_in: schemas_POINT.PointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    point = await crud_POINT.create_point(db=db, userid=user.userid, point_data=point_in)#-->PointFeature
    return point.to_geojson_feature()

@router_linestring.post("/", summary="创建线", response_model=schemas_LINESTRING.LinestringDetail)
async def create_linestring(
    linestring_in: schemas_LINESTRING.LinestringCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    linestring = await crud_LINESTRING.create_linestring(db=db,userid=user.userid ,linestring_data=linestring_in)
    return linestring.to_geojson_feature()

@router_polygon.post("/", summary="创建面", response_model=schemas_POLYGON.PolygonDetail)
async def create_polygon(
    polygon_in: schemas_POLYGON.PolygonCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    polygon_in = await crud_POLYGON.create_polygon(db=db, userid=user.userid, polygon_data=polygon_in)
    return polygon_in.to_geojson_feature()

@router_point.get("/list", summary="查询所有点位")
async def get_all_points(
    page: int = Query(1,ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    points_all,points_count = await crud_POINT.get_all_points(db=db,userid=user.userid,page=page)
    return to_feature_collection(points_all)

@router_linestring.get("/list", summary="查询所有线位")
async def get_all_linestring(
    page: int = Query(1,ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    linestrings_all,linestrings_count = await crud_LINESTRING.get_all_linestrings(db=db,userid=user.userid,page=page)
    return to_feature_collection(linestrings_all)

@router_polygon.get("/list", summary="查询所有面")
async def get_all_polygon(
    page: int = Query(1,ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    polygons_all,polygons_count = await crud_POLYGON.get_all_polygons(db=db,userid=user.userid,page=page)
    return to_feature_collection(polygons_all)

@router_point.get("/{point_id}", summary="根据ID查询点位", response_model=schemas_POINT.PointDetail)
async def get_point_detail(
    point_id: int,
    output_coord_sys: int = Query(default=None, description="输出坐标系SRID，不传则返回原始坐标。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    point = await crud_POINT.get_point_by_id(db=db, point_id=point_id,userid=user.userid,output_coord_sys=output_coord_sys)
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")
    return point.to_geojson_feature()

@router_linestring.get("/{linestring_id}", summary="根据ID查询线", response_model=schemas_LINESTRING.LinestringDetail)
async def get_linestring_detail(
        linestring_id: int,
        output_coord_sys: int = Query(default=None, description="输出坐标系SRID，不传则返回原始坐标。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    linestring = await crud_LINESTRING.get_linestring_by_id(db, linestring_id,userid=user.userid,output_coord_sys=output_coord_sys)
    if not linestring:
        raise HTTPException(status_code=404, detail="线不存在")
    return linestring.to_geojson_feature()

@router_polygon.get("/{polygon_id}", summary="根据ID查询面",response_model=schemas_POLYGON.PolygonDetail)
async def get_polygon_detail(
        polygon_id: int,
        output_coord_sys: int = Query(default=None, description="输出坐标系SRID，不传则返回原始坐标。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    polygon = await crud_POLYGON.get_polygon_by_id(db, polygon_id,userid=user.userid,output_coord_sys=output_coord_sys)
    if not polygon:
        raise HTTPException(status_code=404, detail="面不存在")
    return polygon.to_geojson_feature()

@router_point.put("/{point_id}", summary="更新点位", response_model=schemas_POINT.PointDetail)
async def update_point(
    point_id: int,
    point_in: schemas_POINT.PointUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    point = await crud_POINT.update_point(
        db=db, point_id=point_id, update_data=point_in.model_dump(),userid=user.userid
    )
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")
    return point.to_geojson_feature()

@router_linestring.put("/{linestring_id}", summary="更新线", response_model=schemas_LINESTRING.LinestringDetail)
async def update_linestring(
        linestring_id: int,
        linestring_in: schemas_LINESTRING.LinestringUpdate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    linestring = await crud_LINESTRING.update_linestring(db, linestring_id, linestring_in.model_dump(),userid=user.userid)
    if not linestring:
        raise HTTPException(status_code=404,detail="线不存在")
    return linestring.to_geojson_feature()

@router_polygon.put("/{polygon_id}", summary="更新面", response_model=schemas_POLYGON.PolygonDetail)
async def update_polygon(
        polygon_id: int,
        polygon_in: schemas_POLYGON.PolygonUpdate,
        user: User = Depends(current_user),
        db: AsyncSession = Depends(get_db)
):
    polygon = await crud_POLYGON.update_polygon(db=db, polygon_id=polygon_id, update_data=polygon_in.model_dump(),userid=user.userid)
    if not polygon:
        raise HTTPException(status_code=404,detail="面不存在")
    return polygon.to_geojson_feature()

@router_point.delete("/{point_id}", summary="删除点位")
async def delete_point(
    point_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    result = await crud_POINT.delete_point(db=db, point_id=point_id,userid=user.userid)
    if not result:
        raise HTTPException(status_code=404, detail="点位不存在")
    return {"message": "删除成功", "id": point_id}

@router_linestring.delete("/{linestring_id}", summary="删除线")
async def delete_linestring(
        linestring_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    result = await crud_LINESTRING.delete_linestring(db=db, linestring_id=linestring_id, userid=user.userid)
    if not result:
        raise HTTPException(status_code=404,detail="线不存在")
    return {"message": "删除成功", "id": linestring_id}

@router_polygon.delete("/{polygon_id}", summary="删除面")
async def delete_polygon(
        polygon_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    result = await crud_POLYGON.delete_polygon(db=db, polygon_id=polygon_id,userid=user.userid)
    if not result:
        raise HTTPException(status_code=404,detail="面不存在")
    return {"message": "删除成功", "id": polygon_id}





# ------------------------------
# GIS空间查询接口
# ------------------------------
@router_gis.post("/nearby", summary="附近点位查询")
async def get_nearby(
    query: schemas_GIS.NearbyQuery,
    output_coord_sys: int = Query(default=4326, description="输出坐标系SRID，默认4326(WGS84)。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    page: int =  Query(1,ge=1)
):
    points = await gis.get_nearby(
        db=db, lon=query.lon, lat=query.lat, radius=query.radius, table=PointFeature,userid=user.userid,page=page
    )

    linestring = await gis.get_nearby(
        db=db, lon=query.lon, lat=query.lat, radius=query.radius, table=LinestringFeature,userid=user.userid,page=page
    )

    polygon = await gis.get_nearby(
        db=db, lon=query.lon, lat=query.lat, radius=query.radius, table=PolygonFeature,userid=user.userid,page=page
    )
    return {'point':to_feature_collection(points),
            'linestring':to_feature_collection(linestring),
            'polygon':to_feature_collection(polygon)}



@router_gis.post("/bbox", summary="矩形范围查询")
async def get_by_bbox(
    query: schemas_GIS.BboxQuery,
    output_coord_sys: int = Query(default=4326, description="输出坐标系SRID，默认4326(WGS84)。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1,ge=1)
):
    points = await gis.get_by_bbox(
        db=db, min_lon=query.min_lon, min_lat=query.min_lat, max_lon=query.max_lon, max_lat=query.max_lat,table=PointFeature,userid=user.userid,page=page
    )

    linestring = await gis.get_by_bbox(
        db=db, min_lon=query.min_lon, min_lat=query.min_lat, max_lon=query.max_lon, max_lat=query.max_lat,table=LinestringFeature,userid=user.userid,page=page
    )

    polygon = await gis.get_by_bbox(
        db=db, min_lon=query.min_lon, min_lat=query.min_lat, max_lon=query.max_lon, max_lat=query.max_lat,table=PolygonFeature,userid=user.userid,page=page
    )
    return {'point':to_feature_collection(points),
            'linestring':to_feature_collection(linestring),
            'polygon': to_feature_collection(polygon)}


@router_gis.get("/intersect" ,summary="判断要素相交")
async def get_by_geometry(
        table_1: LayerName = Query(...,description="范围图层、要素"),
        table_2: LayerName = Query(...,description="查询图层、要素"),
        output_coord_sys: int = Query(default=4326, description="输出坐标系SRID，默认4326(WGS84)。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
        db: AsyncSession = Depends(get_db),user: User = Depends(current_user),
        table1_id: int = Query(None,description="范围图层、要素id，不填则所有要素合并去查询"),
        page: int = Query(1,ge=1)
):
#table_1自动获取成员LayerName.point
    table_1 = LAYER_MODEL_MAP[table_1]
    table_2 = LAYER_MODEL_MAP[table_2]

    geometry = await gis.get_by_geometry(db=db,userid=user.userid,table_1=table_1,table_2=table_2,table1_id=table1_id,page=page)
    return to_feature_collection(geometry)

@router_gis.get("/distance",summary="要素距离计算 / 要素到要素的最近点投影（第二个图层上，离第一个最近的那个点坐标）")
async def get_geometry_geometry(
        id_1:int = Query(...,description="第一个要素id"),
        id_2:int = Query(...,description="第二个要素id"),
        table_1: LayerName = Query(...,description="第一个要素所在图层"),
        table_2: LayerName = Query(...,description="第一个要素所在图层"),
        db: AsyncSession = Depends(get_db),user: User = Depends(current_user)
):
    table_1 = LAYER_MODEL_MAP[table_1]
    table_2 = LAYER_MODEL_MAP[table_2]

    result = await gis.get_geometry_geometry(db=db,userid=user.userid,table_1=table_1,table_2=table_2,id_1=id_1,id_2=id_2)
    if result is None:
        raise HTTPException(status_code=404,detail="某个id不存在")
    distance, closest_point = result if result is not None else (0.0, None)

    return {
        "distance": distance,
        "closest_point": closest_point
    }

@router_gis.get("/include",summary="要素包含查询（第二个要素、图层哪些完全在 第一个要素、图层里面）")
async def get_geometry_in_geometry(
        table_1:LayerName = Query(...,description="第一个要素、图层"),
        table_2:LayerName = Query(...,description="第二个要素、图层"),
        table1_id:int = Query(None,description="第一个要素、图层id"),
        output_coord_sys: int = Query(default=4326, description="输出坐标系SRID，默认4326(WGS84)。常用：4326(WGS84), 4490(CGCS2000), 3857(Web墨卡托)"),
        db: AsyncSession = Depends(get_db),user: User = Depends(current_user),
        page: int = Query(1,ge=1)
):
    table_1 = LAYER_MODEL_MAP[table_1]
    table_2 = LAYER_MODEL_MAP[table_2]

    in_geometry = await gis.geometry_in_geometry(db=db,table_1=table_1,table_2=table_2,userid=user.userid,table1_id=table1_id,page=page)
    if in_geometry is None:
        raise HTTPException(status_code=404,detail="id不存在")
    return to_feature_collection(in_geometry)


@router_gis.get("/transform", summary="坐标转换（支持任意SRID）")
async def transform_coord(
        layer: LayerName = Query(..., description="图层类型：point、line、polygon"),
        target_srid: int = Query(..., description="目标坐标系SRID，支持任意PostGIS已注册的SRID。常用：4326(WGS84)、4490(CGCS2000)、3857(Web墨卡托)"),
        feature_ids: str = Query(default=None, description="指定要素ID，多个用逗号分隔，如 1,2,3。不传则查询全部"),
        page: int = Query(1, ge=1),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    """将数据库中的要素坐标转换到目标坐标系后返回，自动识别源坐标系"""
    if not await validate_srid(db, target_srid):
        raise HTTPException(status_code=400, detail=f"目标坐标系 SRID {target_srid} 不存在，请检查是否为有效的PostGIS SRID")

    model = LAYER_MODEL_MAP[layer]
    ids = [int(i.strip()) for i in feature_ids.split(",")] if feature_ids else None

    features = await transform_features(
        db=db, model=model, target_srid=target_srid,
        userid=user.userid, feature_ids=ids, page=page
    )
    return to_feature_collection(features)


@router_gis.get("/{linestring_id}/length",summary="计算线长度")
async def get_linestring_length(linestring_id: int, db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    length = await gis.get_linestring_length(db=db, linestring_id=linestring_id,userid=user.userid)
    if not length:
        raise HTTPException(status_code=404,detail="线不存在")
    return {"id" : linestring_id, "length:" : length}

@router_gis.get("/{polygon_id}/area",summary="计算面积")
async def get_polygon_area(polygon_id: int, db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    area = await gis.get_polygon_area(db=db, polygon_id=polygon_id,userid=user.userid)
    if not area:
        raise HTTPException(status_code=404,detail="面不存在")
    return {"id" : polygon_id, "area:" : area}

@router_gis.post("/batch/import-excel",summary="导入要素(Excel/CSV，支持coord_sys列指定坐标系)")
async def import_(
        file: UploadFile,
        type_:LayerName = Query(..., description="导入类型:point、line、polygon"),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)):
    if not file:
        raise HTTPException(status_code=400,detail="文件为空")

    try:
        if type_== LayerName.point:
            point = await gis.import_file_point(db=db, file=file, userid=user.userid)
            return {"message": point}
        elif type_== LayerName.line:
            linestring = await gis.import_file_linestring(db=db, file=file, userid=user.userid)
            return {"message": linestring}
        elif type_== LayerName.polygon:
            polygon = await gis.import_file_polygon(db=db, file=file, userid=user.userid)
            return {"message": polygon}
        else:
            raise HTTPException(status_code=400,detail=f"导入类型不支持：{type_}，仅支持：point、line、polygon")
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400,detail=str(e))


@router_gis.post("/batch/import-shapefile", summary="从 Shapefile (.zip) 导入要素（自动识别点/线/面）")
async def import_shapefile(
    file: UploadFile,
    coord_sys: int = Query(default=4326, description="坐标系SRID，默认4326(WGS84)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """上传 .zip 格式 Shapefile（内含 .shp/.shx/.dbf），自动识别几何类型导入"""
    if not file:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        result = await gis.import_shapefile(db=db, file=file, userid=user.userid, coord_sys=coord_sys)
        return {"message": result}
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_gis.post("/batch/import-geojson", summary="从 GeoJSON 文件导入要素（自动识别点/线/面）")
async def import_geojson(
    file: UploadFile,
    coord_sys: int = Query(default=4326, description="坐标系SRID，默认4326(WGS84)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """
    上传 GeoJSON 文件，自动识别 Feature 中的几何类型（Point/LineString/Polygon），
    批量导入到对应的点位/线/面表中。支持 FeatureCollection 和单条 Feature。
    """
    if not file:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        result = await gis.import_geojson(db=db, file=file, userid=user.userid, coord_sys=coord_sys)
        return {"message": result}
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router_gis.get("/summary", summary="数据统计 — 各图层要素数量")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """返回当前用户的点位、线、面要素数量及总数"""
    return await gis.get_summary(db=db, userid=user.userid)


def _build_shapefile_zip(features, layer_name: str) -> bytes:
    """将要素列表打包为 Shapefile zip（.shp/.shx/.dbf），返回字节"""
    import tempfile
    import zipfile
    import os
    import shapefile

    geom_type_map = {
        "Point": shapefile.POINT, "MultiPoint": shapefile.MULTIPOINT,
        "LineString": shapefile.POLYLINE, "MultiLineString": shapefile.POLYLINE,
        "Polygon": shapefile.POLYGON, "MultiPolygon": shapefile.POLYGON,
    }

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        base = os.path.join(tmpdir, layer_name)

        # 确定 shapefile 类型
        first_geom = to_shape(features[0].geom)
        first_type = first_geom.geom_type
        sf_type = geom_type_map.get(first_type, shapefile.POINT)

        w = shapefile.Writer(base, shapeType=sf_type)
        w.field("id", "N", 10)
        w.field("name", "C", "100")
        w.field("address", "C", "255")
        w.field("coord_sys", "N", 10)
        w.field("create_tm", "C", "30")
        w.field("update_tm", "C", "30")

        for f in features:
            g = to_shape(f.geom)
            gt = g.geom_type

            if gt in ("Point",):
                w.point(g.x, g.y)
            elif gt in ("MultiPoint",):
                pts = [(p[0], p[1]) for p in g.coords]
                w.multipoint(pts)
            elif gt in ("LineString",):
                w.line([list(g.coords)])
            elif gt in ("MultiLineString",):
                w.line([list(line.coords) for line in g.geoms])
            elif gt in ("Polygon",):
                w.poly([list(g.exterior.coords)])
            elif gt in ("MultiPolygon",):
                parts = [list(p.exterior.coords) for p in g.geoms]
                # shapefile format: outer ring of first polygon + potentially inner rings
                w.poly(parts)

            w.record(
                f.id,
                f.name or "",
                f.address or "",
                f.coord_sys,
                f.create_time.isoformat() if f.create_time else "",
                f.update_time.isoformat() if f.update_time else "",
            )

        w.close()

        # 打包所有相关文件
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                path = base + ext
                if os.path.exists(path):
                    zf.write(path, layer_name + ext)
        bio.seek(0)
        return bio.getvalue()


@router_gis.get("/export", summary="导出要素数据（Shapefile / GeoJSON / Excel / CSV）")
async def export_features(
    layer: LayerName = Query(..., description="图层类型：point、line、polygon"),
    fmt: str = Query("geojson", alias="format", description="导出格式：shapefile、geojson、xlsx、csv"),
    output_coord_sys: int = Query(default=None, description="输出坐标系SRID，不传则返回原始坐标"),
    feature_ids: str = Query(default=None, description="指定要素ID，多个用逗号分隔，不传则导出全部"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user),
):
    """导出当前用户指定图层的要素数据，支持 Shapefile / GeoJSON / Excel / CSV 四种格式"""
    model = LAYER_MODEL_MAP[layer]

    if output_coord_sys is not None and not await validate_srid(db, output_coord_sys):
        raise HTTPException(status_code=400, detail=f"坐标系 SRID {output_coord_sys} 不存在")

    ids = [int(i.strip()) for i in feature_ids.split(",")] if feature_ids else None

    features = await gis.export_features(
        db=db, model=model, userid=user.userid,
        target_srid=output_coord_sys, feature_ids=ids,
    )

    if not features:
        raise HTTPException(status_code=404, detail="没有可导出的数据")

    # 获取图层名称用于文件名
    layer_name_map = {LayerName.point: "point", LayerName.line: "linestring", LayerName.polygon: "polygon"}
    layer_name = layer_name_map[layer]

    if fmt == "geojson":
        fc = to_feature_collection(features)
        content = json.dumps(fc, ensure_ascii=False, indent=2).encode("utf-8")
        return Response(
            content=content,
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{layer_name}_export.geojson"'}
        )

    # Excel / CSV: 构建统一的 DataFrame
    rows = []
    for f in features:
        geom_shapely = to_shape(f.geom)
        row = {
            "id": f.id,
            "name": f.name,
            "address": f.address,
            "coord_sys": f.coord_sys,
            "create_time": f.create_time.isoformat() if f.create_time else None,
            "update_time": f.update_time.isoformat() if f.update_time else None,
            "geom_wkt": geom_shapely.wkt,
        }
        if hasattr(geom_shapely, 'x') and hasattr(geom_shapely, 'y'):
            row["lon"] = geom_shapely.x
            row["lat"] = geom_shapely.y
        rows.append(row)

    df = pandas.DataFrame(rows)

    if fmt == "csv":
        content = df.to_csv(index=False).encode("utf-8-sig")
        media_type = "text/csv"
        filename = f"{layer_name}_export.csv"
    elif fmt == "xlsx":
        bio = io.BytesIO()
        with pandas.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=layer_name)
        content = bio.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{layer_name}_export.xlsx"
    elif fmt == "shapefile":
        content = _build_shapefile_zip(features, layer_name)
        media_type = "application/zip"
        filename = f"{layer_name}_export.zip"
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式：{fmt}，仅支持 shapefile、geojson、xlsx、csv")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


