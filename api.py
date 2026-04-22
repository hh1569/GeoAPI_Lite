from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from shapely.geometry import mapping
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database import get_db
from schemas import schemas_POINT,schemas_LINESTRING,schemas_POLYGON,schemas_GIS,schemas_USER
from crud import crud_POINT, crud_LINESTRING,crud_POLYGON,gis,crud_user,crud_token
from models import PointFeature, LinestringFeature, PolygonFeature, User
from utils.auth import current_user
from utils.geojson import to_feature_collection
from utils.mapping_table import LayerName,LAYER_MODEL_MAP
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
async def get_all_points(page: int = Query(1,ge=1),db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    points_all,points_count = await crud_POINT.get_all_points(db=db,userid=user.userid,page=page)
    return  to_feature_collection(points_all)

@router_linestring.get("/list", summary="查询所有线位")
async def get_all_linestring(page: int = Query(1,ge=1),db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    linestrings_all,linestrings_count = await crud_LINESTRING.get_all_linestrings(db=db,userid=user.userid,page=page)
    return to_feature_collection(linestrings_all)

@router_polygon.get("/list", summary="查询所有面")
async def get_all_polygon(page: int = Query(1,ge=1),db: AsyncSession = Depends(get_db),user: User = Depends(current_user)):
    polygons_all,polygons_count = await crud_POLYGON.get_all_polygons(db=db,userid=user.userid,page=page)
    return to_feature_collection(polygons_all)

@router_point.get("/{point_id}", summary="根据ID查询点位", response_model=schemas_POINT.PointDetail)
async def get_point_detail(
    point_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_user)
):
    point = await crud_POINT.get_point_by_id(db=db, point_id=point_id,userid=user.userid)
    if not point:
        raise HTTPException(status_code=404, detail="点位不存在")
    return point.to_geojson_feature()

@router_linestring.get("/{linestring_id}", summary="根据ID查询线", response_model=schemas_LINESTRING.LinestringDetail)
async def get_linestring_detail(
        linestring_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    linestring = await crud_LINESTRING.get_linestring_by_id(db, linestring_id,userid=user.userid)
    if not linestring:
        raise HTTPException(status_code=404, detail="线不存在")
    return linestring.to_geojson_feature()

@router_polygon.get("/{linestring_id}", summary="根据ID查询面",response_model=schemas_POLYGON.PolygonDetail)
async def get_linestring_detail(
        polygon_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(current_user)
):
    polygon = await crud_POLYGON.get_polygon_by_id(db, polygon_id,userid=user.userid)
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
        db: AsyncSession = Depends(get_db),user: User = Depends(current_user),
        page: int = Query(1,ge=1)
):
    table_1 = LAYER_MODEL_MAP[table_1]
    table_2 = LAYER_MODEL_MAP[table_2]

    in_geometry = await gis.geometry_in_geometry(db=db,table_1=table_1,table_2=table_2,userid=user.userid,table1_id=table1_id,page=page)
    if in_geometry is None:
        raise HTTPException(status_code=404,detail="id不存在")
    return to_feature_collection(in_geometry)

            
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

@router_gis.post("/batch/import-excel",summary="导入要素(格式：116.300 39.900)")
async def import_(
        file: UploadFile,
        type_:LayerName = Query(..., description="导入类型:point、lines、polygon"),
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
            raise HTTPException(status_code=400,detail=f"导入类型不支持：{type_}，仅支持：点、线、面，不可以多字少字")
    except TypeError as e:
        raise HTTPException(status_code=400,detail=str(e))


