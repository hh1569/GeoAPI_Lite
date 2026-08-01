"""
抓取高德 POI → 存入 GeoAPI_Lite 点表

用法示例：
    # 抓 4 页（约 100 条）安顺市学校，归到第一个用户
    python scripts/fetch_amap_poi.py

    # 抓 10 页贵阳的医院，归到指定用户
    python scripts/fetch_amap_poi.py --keywords 医院 --city 贵阳市 --pages 10 --username 你的用户名

前置条件：
    1. .env 中已配置 AMAP_KEY（高德 Web 服务 Key）和数据库连接
    2. 数据库已有至少一个用户（用于点位归属 userid）
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 确保能 import 项目根目录的模块（直接运行 scripts/ 下的脚本时必需）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from crud.crud_POINT import create_point
from database import AsyncSessionLocal
from models import PointFeature, User
from schemas.schemas_POINT import PointCreate
from utils.amap_client import search_poi_many


async def get_user_id(username: str | None) -> int:
    """取用户名对应的 userid，未指定则取第一个用户"""
    async with AsyncSessionLocal() as db:
        if username:
            result = await db.execute(select(User).where(User.name == username))
            user = result.scalar_one_or_none()
        else:
            result = await db.execute(select(User).order_by(User.userid).limit(1))
            user = result.scalar_one_or_none()
    if not user:
        raise SystemExit(f"未找到可用用户（{'用户名: ' + username if username else '数据库无用户'}），请先通过 /auth 注册用户")
    return user.userid


async def existing_names(db, userid: int) -> set[str]:
    """查该用户已有点位名称，用于幂等跳过"""
    result = await db.execute(select(PointFeature.name).where(PointFeature.userid == userid))
    return {row[0] for row in result.all()}


async def main():
    parser = argparse.ArgumentParser(description="抓取高德 POI 存入点表")
    parser.add_argument("--keywords", default=None, help="搜索关键词（按名称搜，与 --types 二选一）")
    parser.add_argument("--types", default=None, help="高德 POI 类型码，如 1412=学校、050000=风景名胜、060100=餐饮")
    parser.add_argument("--city", default="520400", help="搜索城市名或adcode，默认520400=安顺市（adcode更稳定）")
    parser.add_argument("--pages", type=int, default=4, help="抓取页数（每页25条），默认：4")
    parser.add_argument("--username", default=None, help="点位归属用户名，默认取第一个用户")
    args = parser.parse_args()

    if not args.keywords and not args.types:
        raise SystemExit("必须提供 --keywords 或 --types 其中之一")

    print(f"* 开始抓取高德 POI：类型[{args.types or '-'}] 关键词[{args.keywords or '-'}] 城市[{args.city}] 页数[{args.pages}]")
    pois = search_poi_many(args.keywords, city=args.city, pages=args.pages, types=args.types)
    print(f"  OK 高德返回 {len(pois)} 条（已去重、已转 WGS84）")

    if not pois:
        print("  X 未抓到数据，请检查 Key / 关键词 / 城市")
        return

    userid = await get_user_id(args.username)
    print(f"  OK 点位归属用户 userid={userid}")

    inserted, skipped = 0, 0
    async with AsyncSessionLocal() as db:
        existing = await existing_names(db, userid)

        for poi in pois:
            # 幂等：同名点位已存在则跳过
            if poi["name"] in existing:
                skipped += 1
                continue

            point = PointCreate(
                name=poi["name"],
                address=poi["address"] or f"{poi['province']}{poi['city']}{poi['district']}",
                geom=f"POINT({poi['lon']} {poi['lat']})",   # WGS84，与项目默认 4326 一致
                coord_sys=4326,
            )
            await create_point(db, userid, point)   # 每次独立 commit，量小可接受
            existing.add(poi["name"])
            inserted += 1

        # 汇总统计
        total = (await db.execute(
            select(PointFeature).where(PointFeature.userid == userid)
        )).scalars().all()

    print(f"\n完成 完成：本次入库 {inserted} 条，跳过重复 {skipped} 条")
    print(f"   该用户点表现有 {len(total)} 条，示例：")
    for p in total[:5]:
        lon, lat = p.get_lon("geom"), p.get_lat("geom")
        print(f"   - [{p.id}] {p.name}  ({lon:.6f}, {lat:.6f})  {p.address}")


if __name__ == "__main__":
    asyncio.run(main())
