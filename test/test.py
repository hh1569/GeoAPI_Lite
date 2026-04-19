from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, select
from geoalchemy2 import Geometry
import asyncio

DB_URI = "postgresql+asyncpg://postgres:123456@localhost:5432/gis_"


engine = create_async_engine(DB_URI,echo=True)
AsyncSessionLocal = async_sessionmaker(engine,class_=AsyncSession, expire_on_commit=False)

from geoalchemy2.shape import to_shape

class Base(DeclarativeBase):
    __abstract__ = True#这个类不会在数据库里创建表
    # 1. 获取 WKT 格式：POINT(120 30)
    def get_wkt(self):

        return to_shape(self.geom).wkt

    # 2. 获取经度
    def get_lon(self):

        return to_shape(self.geom).x

    # 3. 获取纬度
    def get_lat(self):

        return to_shape(self.geom).y

    # 4. 转成可返回 JSON 的字典
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "geom": self.get_wkt(),  # 直接用自己的函数
            "lon": self.get_lon(),
            "lat": self.get_lat()
        }



class Point(Base):
    __tablename__ = "points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str]= mapped_column(String)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326))

async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

#建表
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_table()  # 调用建表函数，自动创建所有数据库表
    print("建表完成：所有ORM模型对应的数据库表已创建/更新")
    yield  # 生命周期分界点：暂停执行，进入应用运行阶段（处理接口请求）
    print("应用关闭：开始释放资源（如数据库连接池）")


async def get_db():
    async with AsyncSessionLocal() as session:#AsyncSessionLocal() 里的括号，本质是 **“调用 / 启动” 的信号
        try:
            yield session
        except Exception:
            await session.rollback()#接口操作出错时，“撤销” 所有没提交的修改
            raise
        finally:
            await session.close()


app = FastAPI(lifespan=lifespan)

from pydantic import BaseModel,Field

class geo(BaseModel):
    name: str
    geom: str = Field(...,description='')

@app.post("/")
async def add_point_api(point: geo,db: AsyncSession = Depends(get_db)):
    db.add(Point(name=point.name,geom=point.geom))
    await db.commit()
    return 0


@app.get("/points")
async def get_all_points(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Point))
    points = result.scalars().all()  # 拿到所有点

    return [
        {
            "id": p.id,
            "name": p.name,
            "geom": str(p.geom)  # 必须转字符串
        }
        for p in points
    ]

@app.get("/points/{id}")
async def get_one_point(id: int, db: AsyncSession = Depends(get_db)):
    # 用 select 写法
    query = select(Point).where(Point.id == id)
    point = (await db.execute(query)).scalar_one_or_none()

    # 函数全部来自基类！直接用！
    return point.to_dict()

# uvicorn test:app --reload
#POINT(120 30)

