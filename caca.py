
from typing import TypeVar, Any, Dict, Union
from pydantic import BaseModel, Field, PrivateAttr, create_model


Model = TypeVar('Model', bound='BaseModel')

class RefToModelBase(BaseModel):

    ref: str = Field(alias="$ref")
    target: BaseModel
    target_type: type[Model]
    tainted: bool = False

    def dict(self, *args, **kwargs):
        return {"$ref": self.ref}

    def __getattr__(self, item):
        self.target = self.target or self.target_type.parse_file(self.ref)
        return getattr(self.target, item)

    def __setattr__(self, key, value):
        if key in self.__fields__:
            object.__setattr__(self, key, value)
            return
        self.target = self.target or self.target_type.parse_file(self.ref)
        self.tainted = True
        object.__setattr__(self.target, key, value)

def lazy_loading(model_clazz):

    new_model = create_model(
        f"RefTo{model_clazz.__name__}",
        __base__=RefToModelBase,
        target=(model_clazz, None),
        target_type=(type[Model], model_clazz)
    )
    return new_model

class Actor(BaseModel):
    birth_year: int
    filmography: Dict[Any, Any]
    first_name: str
    is_funny: bool
    last_name: str
    movies: Dict[Any, Any]
    spouses: Dict[Any, Any]

RefToActor = lazy_loading(Actor)

class Model(BaseModel):

    actors: Dict[str, Union[Actor, RefToActor]]

m = Model.parse_obj({
    "actors": {
        "charlie_chaplin": {"$ref": "output/root/actors/charlie_chaplin.json"}
    }
})


print("--")
print(m.actors["charlie_chaplin"].first_name)
print("--")
print(m.actors["charlie_chaplin"])
print("--")
m.actors["charlie_chaplin"].first_name = "Charles"
print('m.actors["charlie_chaplin"].first_name = "Charles"')
print("--")
print(m.actors["charlie_chaplin"])
print("--")
print(m.json())
print("--")
