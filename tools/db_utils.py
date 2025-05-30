from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.backend_settings import settings 




engine = create_engine(
    settings.database_url, 
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()

def create_db_and_tables():
    """
    在数据库中创建所有定义的表（如果它们尚不存在）。
    这个函数应该在应用启动时被调用一次。
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("数据库表已成功检查/创建。") 
    except Exception as e:
        print(f"创建数据库表失败: {e}") 
        

def get_db():
    """
    FastAPI 依赖项，用于获取数据库会话。
    它确保每个请求都有一个独立的数据库会话，并在请求完成后关闭它。
    """
    db = SessionLocal()
    try:
        yield db  
    finally:
        db.close() 