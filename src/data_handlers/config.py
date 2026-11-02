from pydantic import BaseModel


class PostgresConfig(BaseModel):
    host: str
    port: int
    dbname: str
    user: str
    password: str
    driver: str = "psycopg"

    def build_url(self) -> str:
        return (
            f"postgresql+{self.driver}://"
            f"{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
        )


class ClickhouseConfig(BaseModel):
    host: str
    port: int = 8123
    username: str = "default"
    password: str = ""
    database: str = "default"
    secure: bool = False
    connect_timeout: int = 10


class MongoConfig(BaseModel):
    host: str
    port: int = 27017
    username: str | None = None
    password: str | None = None
    database: str = "shop"
    auth_source: str = "admin"
    direct_connection: bool = True

    def build_uri(self) -> str:
        if self.username and self.password:
            credentials = f"{self.username}:{self.password}@"
        else:
            credentials = ""

        uri = f"mongodb://{credentials}{self.host}:{self.port}/"

        params = {
            "authSource": self.auth_source,
            "directConnection": str(self.direct_connection).lower(),
        }

        return uri + "?" + "&".join(f"{key}={value}" for key, value in params.items())


class RedisConfig(BaseModel):
    host: str
    port: int = 6379
    db: int = 0
    username: str | None = None
    password: str | None = None
    ssl: bool = False
    socket_timeout: int = 10
    socket_connect_timeout: int = 10
