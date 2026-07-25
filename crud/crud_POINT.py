from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
from models import PointFeature


def _transform_geom(model, output_coord_sys):
    """返回转换后的geom列"""
    if output_coord_sys != 4326:
        return func.ST_Transform(model.geom, output_coord_sys).label('geom')
    return model.geom


def _to_point(row, output_coord_sys):
    """将查询结果转为PointFeature对象"""
    point = PointFeature()
    for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
        setattr(point, col, getattr(row, col))
    return point


# ------------------------------
# 基础CRUD
# ------------------------------
async def create_point(db: AsyncSession,userid: int,point_data) -> PointFeature:
    """创建点位，支持坐标系转换"""
    data = point_data.model_dump()
    coord_sys = data.pop('coord_sys', 4326)

    if coord_sys != 4326:
        data['geom'] = func.ST_Transform(
            func.ST_SetSRID(func.ST_GeomFromText(data['geom']), coord_sys), 4326
        )

    add_point = PointFeature(**data, userid=userid, coord_sys=coord_sys)
    db.add(add_point)
    await db.commit()
    await db.refresh(add_point)
    return add_point


async def get_point_by_id(db: AsyncSession, point_id: int,userid: int, output_coord_sys: int = 4326):
    """根据ID查询点位"""
    geom_col = _transform_geom(PointFeature, output_coord_sys)
    result = await db.execute(
        select(PointFeature.id, PointFeature.userid, PointFeature.name,
               PointFeature.address, PointFeature.coord_sys,
               PointFeature.create_time, PointFeature.update_time, geom_col)
        .where(PointFeature.id == point_id, PointFeature.userid == userid)
    )
    row = result.one_or_none()
    return _to_point(row, output_coord_sys) if row else None


async def get_all_points(db: AsyncSession,userid: int,page: int = 1, output_coord_sys: int = 4326):
    """查询所有点位"""
    skip = (page-1)*6
    geom_col = _transform_geom(PointFeature, output_coord_sys)

    result_all = await db.execute(
        select(PointFeature.id, PointFeature.userid, PointFeature.name,
               PointFeature.address, PointFeature.coord_sys,
               PointFeature.create_time, PointFeature.update_time, geom_col)
        .where(PointFeature.userid == userid)
        .order_by(PointFeature.id).offset(skip).limit(6)
    )
    points = [_to_point(row, output_coord_sys) for row in result_all.all()]

    result_count = await db.execute(select(func.count(PointFeature.id)).where(PointFeature.userid == userid))
    return points, result_count.scalar()


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

