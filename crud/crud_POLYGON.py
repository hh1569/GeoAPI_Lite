from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import PolygonFeature

# ------------------------------
# 基础CRUD
# ------------------------------
async def create_polygon(db: AsyncSession, polygon_data,userid: int):
    """创建面"""
    add_polygon = PolygonFeature(**polygon_data.model_dump(),userid=userid)
    db.add(add_polygon)
    await db.commit()
    await db.refresh(add_polygon)
    return add_polygon

async def get_polygon_by_id(db: AsyncSession, polygon_id: int,userid: int):
    """根据ID查询面"""
    result = await db.execute(select(PolygonFeature).
    where(PolygonFeature.id == polygon_id,PolygonFeature.userid == userid))
    return result.scalar_one_or_none()

async def get_all_polygons(db: AsyncSession,userid: int,page: int = 1):
    """查询所有面"""

    stmt = (page-1)*6

    result_all = await db.execute(select(PolygonFeature)
                    .where(PolygonFeature.userid == userid)
                    .order_by(PolygonFeature.id).offset(stmt).limit(6))

    result_count = await db.execute(select(func.count(PolygonFeature.id)).where(PolygonFeature.userid == userid))
    return result_all.scalars().all(), result_count.scalar()

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


