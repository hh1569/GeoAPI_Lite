from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
from models import PointFeature


# ------------------------------
# 基础CRUD
# ------------------------------
async def create_point(db: AsyncSession,userid: int,point_data) -> PointFeature:
    """创建点位"""
    add_point = PointFeature(**point_data.model_dump(),userid=userid)
    db.add(add_point)
    await db.commit()
    await db.refresh(add_point)
    return add_point

async def get_point_by_id(db: AsyncSession, point_id: int,userid: int) -> PointFeature | None:
    """根据ID查询点位"""
    result = await db.execute(select(PointFeature).
        where(PointFeature.id == point_id,PointFeature.userid == userid))
    return result.scalar_one_or_none()

async def get_all_points(db: AsyncSession,userid: int):
    """查询所有点位"""
    result_all = await db.execute(select(PointFeature).where(PointFeature.userid == userid))
    result_count = await db.execute(select(func.count(PointFeature.id)).where(PointFeature.userid == userid))
    return result_all.scalars().all(), result_count.scalar()

async def update_point(db: AsyncSession, point_id: int, update_data: dict,userid: int) -> PointFeature | None:
    """更新点位"""
    point = await get_point_by_id(db=db, point_id=point_id,userid=userid)
    if not point:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(point, key, value)
    await db.commit()
    await db.refresh(point)
    return point

async def delete_point(db: AsyncSession, point_id: int,userid: int) -> bool:
    """删除点位"""
    point = await get_point_by_id(db, point_id ,userid=userid)
    if not point:
        return False
    await db.delete(point)
    await db.commit()
    return True



