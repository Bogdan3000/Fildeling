from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    """Корневой маршрут."""
    return {"message": "Hello World"}

@router.get("/hello/{name}")
async def say_hello(name: str):
    """Приветствие по имени."""
    return {"message": f"Hello {name}"}
