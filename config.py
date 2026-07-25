from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # 连接池配置
    POOL_SIZE: int
    MAX_OVERFLOW: int
    ECHO_SQL: bool

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        """异步数据库连接字符串"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# 全局配置实例
settings = Settings()
print(settings.ASYNC_DATABASE_URI)