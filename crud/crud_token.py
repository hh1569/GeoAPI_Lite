from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User,UserToken
from utils import encryption
from crud.crud_user import get_user_userid,get_user_username

async def create_token(db: AsyncSession, user_id: int):
    """生成token"""
    token = str(uuid4())
    expires_at = datetime.now() + timedelta(days=7)
    query = select(UserToken).where(UserToken.userid == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()

    if user_token :
        user_token.token = token
        user_token.expires_at = expires_at
        await db.commit()

    else:
        user_token = UserToken(userid=user_id, token=token,expires_at=expires_at)
        db.add(user_token)
        await db.commit()

    return token



async def authenticate_user_(db: AsyncSession, userid: int, password: str):
    """验证密码"""

    user = await get_user_userid(db, userid)
    if not user:
        return None
    if not encryption.verify_password(password, user.password):
        return None

    return user

async def authenticate_user(db: AsyncSession, account: str | int, password: str):
    """
    验证密码（支持 用户名 / 用户ID 两种方式登录）
    即使用户名是纯数字，也不会出错
    """
    # 1. 先尝试按【用户名】查
    user = await get_user_username(db, str(account))
    # 2. 用户名不存在 → 再尝试按【ID】查
    if not user:
        try:
            userid = int(account)
            user = await get_user_userid(db, userid)
        except (ValueError, TypeError):
            user = None
    if not user:
        return None
    if not encryption.verify_password(password, user.password):
        return None
    return user


async def get_user_by_token(db: AsyncSession, token: str):
    """根据token查询用户"""
    # 1. 查询token记录
    stmt_token = select(UserToken).where(UserToken.token == token)
    result = await db.execute(stmt_token)
    db_token = result.scalar_one_or_none()

    if not db_token:
        return None
    # 使用UTC时间比较，避免时区问题
    if datetime.now() > db_token.expires_at:
        return None  # token已过期

    # 3. token有效，查询并返回用户
    stmt_user = select(User).where(User.userid == db_token.userid)
    result = await db.execute(stmt_user)
    db_user = result.scalar_one_or_none()

    return db_user

