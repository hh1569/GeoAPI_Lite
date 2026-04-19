from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException

from schemas.schemas_USER import UserCreate, UserDetail, UserUpdate
from models import User,UserToken
from utils import encryption


async def get_user_username(db: AsyncSession,username: str):
    """根据用户名查找用户"""
    stmt = select(User).where(User.name == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_user_userid(db: AsyncSession,userid: int):
    """根据id查找用户"""
    stmt = select(User).where(User.userid == userid)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data: UserCreate):
    """创建用户"""
    hashed_password = encryption.get_hashed_password(user_data.password)
    add_user = User(name=user_data.name,password=hashed_password,phone=user_data.phone)
    db.add(add_user)
    await db.commit()
    await db.refresh(add_user)
    return add_user



async def put_update_user(db: AsyncSession, userid: int, user_data: UserUpdate):
    """更新用户信息"""
    stmt_user = update(User).where(User.userid == userid).values(**user_data.model_dump(
        exclude_unset=True,  # 忽略所有值为 None 的字段（不会出现在最终字典里）
        exclude_none=True,  # 忽略「没有被显式赋值」的字段（只保留「主动设置过」的字段）
    ))
    result = await db.execute(stmt_user)
    await db.commit()

    if result.rowcount == 0:

        raise HTTPException(status_code=400, detail="更新失败")

    result_user = await get_user_userid(db=db, userid=userid)

    return result_user



async def update_password(db: AsyncSession, user: User, old_password: str, new_password: str):
    """修改密码"""
    if not encryption.verify_password(plain_password=old_password, hashed_password=user.password):
        return False

    hashed_password = encryption.get_hashed_password(new_password)
    user.password = hashed_password
    db.add(user)  # SQLAlchemy真正接管User对象
    a = encryption.verify_password(plain_password=new_password, hashed_password=hashed_password)
    await db.commit()
    await db.refresh(user)
    return a

