from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import LinestringFeature


def _transform_geom(model, output_coord_sys):
    """返回转换后的geom列"""
    if output_coord_sys != 4326:
        return func.ST_Transform(model.geom, output_coord_sys).label('geom')
    return model.geom


def _to_linestring(row):
    """将查询结果转为LinestringFeature对象"""
    obj = LinestringFeature()
    for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
        setattr(obj, col, getattr(row, col))
    return obj


async def create_linestring(db: AsyncSession, linestring_data, userid: int) -> LinestringFeature:
    """创建线，支持坐标系转换"""
    data = linestring_data.model_dump()
    coord_sys = data.pop('coord_sys', 4326)

    if coord_sys != 4326:
        data['geom'] = func.ST_Transform(
            func.ST_SetSRID(func.ST_GeomFromText(data['geom']), coord_sys), 4326
        )

    add_linestring = LinestringFeature(**data, userid=userid, coord_sys=coord_sys)
    db.add(add_linestring)
    await db.commit()
    await db.refresh(add_linestring)
    return add_linestring


async def get_all_linestrings(db: AsyncSession,userid: int,page: int = 1, output_coord_sys: int = 4326):
    """查询所有线"""
    skip = (page-1)*6
    geom_col = _transform_geom(LinestringFeature, output_coord_sys)

    result_all = await db.execute(
        select(LinestringFeature.id, LinestringFeature.userid, LinestringFeature.name,
               LinestringFeature.address, LinestringFeature.coord_sys,
               LinestringFeature.create_time, LinestringFeature.update_time, geom_col)
        .where(LinestringFeature.userid == userid)
        .order_by(LinestringFeature.id).offset(skip).limit(6)
    )
    linestrings = [_to_linestring(row) for row in result_all.all()]

    result_count = await db.execute(select(func.count(LinestringFeature.id)).where(LinestringFeature.userid == userid))
    return linestrings, result_count.scalar()


async def get_linestring_by_id(db: AsyncSession, linestring_id: int,userid: int, output_coord_sys: int = 4326):
    """根据ID查询线"""
    geom_col = _transform_geom(LinestringFeature, output_coord_sys)
    result = await db.execute(
        select(LinestringFeature.id, LinestringFeature.userid, LinestringFeature.name,
               LinestringFeature.address, LinestringFeature.coord_sys,
               LinestringFeature.create_time, LinestringFeature.update_time, geom_col)
        .where(LinestringFeature.id == linestring_id, LinestringFeature.userid == userid)
    )
    row = result.one_or_none()
    return _to_linestring(row) if row else None

async def update_linestring(db: AsyncSession, linestring_id: int, update_data: dict,userid: int) -> LinestringFeature | None:
    """更新线位"""
    linestring = await get_linestring_by_id(db=db, linestring_id=linestring_id,userid=userid)
    if not linestring:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(linestring, key, value)
    await db.commit()
    await db.refresh(linestring)
    return linestring

async def delete_linestring(db: AsyncSession, linestring_id: int,userid: int) -> bool:
    """删除线"""
    linestring= await get_linestring_by_id(db=db, linestring_id=linestring_id,userid=userid)
    if not linestring:
        return False
    await db.delete(linestring)
    await db.commit()
    return True



async def get_linestring_length(db: AsyncSession,linestring_id: int,userid: int):
    """_______"""
    result = await db.execute(select(LinestringFeature.geom).
    where(LinestringFeature.id == linestring_id,LinestringFeature.userid == userid))
    geom = result.scalar_one_or_none()
    if not geom:
        return None
    linestring = to_shape(geom)
    lin_length = linestring.length
    # geojson = length.__geo_interface__   #geojson
    return lin_length













