from fastapi.security import HTTPBearer
from fastapi import Header, Depends, HTTPException,Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

import models
from database import get_db
from crud.crud_token import get_user_by_token


#验证用户登录
# async def current_user(
#         #Header有问题
#         # authorization: str = Header(None, alias="Authorization"),
#         authorization: str = Query(None,description="token"),
#         db: AsyncSession = Depends(get_db)
# ) -> models.User:
#     if not authorization:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")
#     token = authorization.replace("Bearer ","")
#     user = await get_user_by_token(db=db,token=token)
#     if not user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="令牌无效或过期")
#     return user


security = HTTPBearer()#自动检查请求头里有没有 Authorization: Bearer xxx。
async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    """
    从 Authorization: Bearer <token> 请求头中提取并验证用户身份。
    """
    token = credentials.credentials  # 提取 Bearer 后面的纯 token 字符串

    user = await get_user_by_token(db=db, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    return user