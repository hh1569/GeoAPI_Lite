from pydantic import BaseModel, ConfigDict

from models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal  # 你的会话工厂


class Person(BaseModel):
    userid: int
    name: str
    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象属性取值
    )

# 这是 FastAPI 依赖函数，不能直接调用！
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ======================
# 正确测试写法（重点）
# ======================
async def test_query():
    # 1. 获取会话
    async for session in get_db():
        # 2. 构建SQL
        stmt = select(User).where(User.userid == 5)

        # 3. 执行（必须 await）
        result = await session.execute(stmt)

        # 4. 获取结果
        user = result.scalar()
        print(type(user))
        print(user)

        # print(user.userid)
        # print(user.name)

        person = Person.model_validate(user)# ORM 转 Pydantic
        print(person)
        print(type(person))


# 运行异步函数
import asyncio

asyncio.run(test_query())



