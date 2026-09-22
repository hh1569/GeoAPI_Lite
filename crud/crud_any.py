from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func


def _to_point(row, mod):
    """将查询结果转为 ORM 模型对象(点/线/面通用,mod 传入对应模型类)"""
    obj = mod()
    for col in ['id', 'userid', 'name', 'address', 'coord_sys', 'create_time', 'update_time', 'geom']:
        setattr(obj, col, getattr(row, col))
    return obj

# 插入、更新。。。values()参数来自模型
# ------------------------------
# 通用CRUD:sch 为创建入参实例,mod 为对应 ORM 模型类
# ------------------------------
async def create(db: AsyncSession,
                 userid: int,
                 sch,
                 mod
                 ):
    """创建要素，geom 存储用户指定的坐标系，与 coord_sys 一致"""
    data = sch.model_dump()
    coord_sys = data.pop('coord_sys', 4326)#  1. 取出键对应的值,2. 同时从字典里删掉这个键

    data['geom'] = func.ST_SetSRID(func.ST_GeomFromText(data['geom']), coord_sys)#字典更新

    add_lay = mod(**data, userid=userid, coord_sys=coord_sys)
    db.add(add_lay)
    await db.commit()
    await db.refresh(add_lay)
    return add_lay


async def get_by_id(
        models,
        db: AsyncSession,
        lay_id: int,
        userid: int,
        output_coord_sys: int = None):
    """根据ID查询；不传 output_coord_sys 时返回持久化 ORM 实体（可更新/删除），传入则返回转换坐标后的展示对象"""
    if output_coord_sys is not None:
        geom_col = func.ST_Transform(models.geom, output_coord_sys).label('geom')
        result = await db.execute(
            select(models.id, models.userid, models.name,
                   models.address, models.coord_sys,
                   models.create_time, models.update_time, geom_col)
            .where(models.id == lay_id, models.userid == userid)
        )
        row = result.one_or_none()
        return _to_point(row, models) if row else None

    result = await db.execute(
        select(models).where(models.id == lay_id, models.userid == userid)
    )
    return result.scalars().one_or_none()


async def get_all(models, db: AsyncSession, userid: int, page: int = 1, limit: int = 10):
    """查询指定所有单个要素（返回数据库原始坐标，不做坐标转换）"""
    skip = (page-1)*limit

    result_all = await db.execute(
        select(models)
        .where(models.userid == userid)
        .order_by(models.id).offset(skip).limit(limit)
    )
    points = result_all.scalars().all()

    result_count = await db.execute(select(func.count(models.id)).where(models.userid == userid))
    return points, result_count.scalar()

async def get_any(
        db: AsyncSession,
        userid: int,
        mod_list: list[Any],
        page: int = 1,
        limit: int = 10
):
    list_mod = []
    count = 0
    for mod in mod_list:
        mod,s = await get_all(models=mod, db=db, userid=userid, page=page, limit=limit)
        count = count + s
        for i in mod:
            list_mod.append(i)

    return list_mod, count










async def update_lay(models, db: AsyncSession, lay_id: int, update_data: dict, userid: int):
    """更新要素"""
    obj = await get_by_id(models=models, db=db, lay_id=lay_id, userid=userid)
    if not obj:
        return None
    for key, value in update_data.items():
        if value is not None:
            setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_lay(models, db: AsyncSession, lay_id: int, userid: int) -> bool:
    """删除要素"""
    obj = await get_by_id(models=models, db=db, lay_id=lay_id, userid=userid)
    if not obj:
        return False
    await db.delete(obj)
    await db.commit()
    return True
