from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import PolygonFeature


def _transform_geom(model, output_coord_sys):
    """返回转换后的geom列"""
    if output_coord_sys != 4326:
        return func.ST_Transform(model.geom, output_coord_sys).label('geom')
    return model.geom


def _to_polygon(row):
    """将查询结果转为PolygonFeature对象"""
    obj = PolygonFeature()
    for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
        setattr(obj, col, getattr(row, col))
    return obj


async def create_polygon(db: AsyncSession, polygon_data,userid: int):
    """创建面，支持坐标系转换"""
    data = polygon_data.model_dump()
    coord_sys = data.pop('coord_sys', 4326)

    if coord_sys != 4326:
        data['geom'] = func.ST_Transform(
            func.ST_SetSRID(func.ST_GeomFromText(data['geom']), coord_sys), 4326
        )

    add_polygon = PolygonFeature(**data, userid=userid, coord_sys=coord_sys)
    db.add(add_polygon)
    await db.commit()
    await db.refresh(add_polygon)
    return add_polygon


async def get_polygon_by_id(db: AsyncSession, polygon_id: int,userid: int, output_coord_sys: int = 4326):
    """根据ID查询面"""
    geom_col = _transform_geom(PolygonFeature, output_coord_sys)
    result = await db.execute(
        select(PolygonFeature.id, PolygonFeature.userid, PolygonFeature.name,
               PolygonFeature.address, PolygonFeature.coord_sys,
               PolygonFeature.create_time, PolygonFeature.update_time, geom_col)
        .where(PolygonFeature.id == polygon_id, PolygonFeature.userid == userid)
    )
    row = result.one_or_none()
    return _to_polygon(row) if row else None


async def get_all_polygons(db: AsyncSession,userid: int,page: int = 1, output_coord_sys: int = 4326):
    """查询所有面"""
    skip = (page-1)*6
    geom_col = _transform_geom(PolygonFeature, output_coord_sys)

    result_all = await db.execute(
        select(PolygonFeature.id, PolygonFeature.userid, PolygonFeature.name,
               PolygonFeature.address, PolygonFeature.coord_sys,
               PolygonFeature.create_time, PolygonFeature.update_time, geom_col)
        .where(PolygonFeature.userid == userid)
        .order_by(PolygonFeature.id).offset(skip).limit(6)
    )
    polygons = [_to_polygon(row) for row in result_all.all()]

    result_count = await db.execute(select(func.count(PolygonFeature.id)).where(PolygonFeature.userid == userid))
    return polygons, result_count.scalar()


async def update_polygon(db: AsyncSession, polygon_id: int, update_data: dict,userid: int):
    """更新面位"""
    polygon = await get_polygon_by_id(db=db, polygon_id=polygon_id, userid=userid)
    if not polygon:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(polygon, key, value)
    await db.commit()
    await db.refresh(polygon)
    return polygon

async def delete_polygon(db: AsyncSession, polygon_id: int,userid: int) -> bool:
    """删除面"""
    polygon = await get_polygon_by_id(db=db, polygon_id=polygon_id,userid=userid)
    if not polygon:
        return False
    await db.delete(polygon)
    await db.commit()
    return True
