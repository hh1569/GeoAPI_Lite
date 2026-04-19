from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import LinestringFeature

async def create_linestring(db: AsyncSession, linestring_data, userid: int) -> LinestringFeature:
    """创建线"""
    add_linestring = LinestringFeature(**linestring_data.model_dump(),userid=userid)
    db.add(add_linestring)
    await db.commit()
    await db.refresh(add_linestring)
    return add_linestring


async def get_all_linestrings(db: AsyncSession,userid: int):
    """查询所有线"""
    result_all = await db.execute(select(LinestringFeature).where(LinestringFeature.userid == userid))
    result_count = await db.execute(select(func.count(LinestringFeature.id)).where(LinestringFeature.userid == userid))
    return result_all.scalars().all(), result_count.scalar()

async def get_linestring_by_id(db: AsyncSession, linestring_id: int,userid: int) -> LinestringFeature | None:
    """根据ID查询线"""
    result = await db.execute(select
      (LinestringFeature).
      where(LinestringFeature.id == linestring_id,LinestringFeature.userid == userid))
    return result.scalar_one_or_none()

async def update_linestring(db: AsyncSession, linestring_id: int, update_data: dict,userid: int) -> LinestringFeature | None:
    """更新线位"""
    linestring = await get_linestring_by_id(db=db, linestring_id=linestring_id,userid=userid)
    if not linestring:
        return None
    for key, value in update_data.items():
        if value is not None:
            #setattr(对象, 属性名, 值) = 给对象设置属性
            setattr(linestring, key, value)#==linestring.key = value
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













