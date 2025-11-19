from pydantic import BaseModel

class MyModel(BaseModel):
    x: int
    y: str

def test_pydantic():
    m = MyModel(x=1, y="hello")
    assert m.x == 1
    assert m.y == "hello"
