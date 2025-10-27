"""Minimal subset of Pydantic functionality used for GAPx scaffolding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union, get_args, get_origin, get_type_hints

__all__ = ["BaseModel", "Field", "validator"]


class _Missing:
    pass


MISSING = _Missing()


@dataclass
class FieldInfo:
    default: Any = MISSING
    default_factory: Optional[Callable[[], Any]] = None


def Field(default: Any = MISSING, default_factory: Optional[Callable[[], Any]] = None, **_: Any) -> FieldInfo:
    return FieldInfo(default=default, default_factory=default_factory)


ValidatorFunc = Callable[[Type["BaseModel"], Any], Any]


def validator(*fields: str, pre: bool = False) -> Callable[[ValidatorFunc], ValidatorFunc]:
    def decorator(func: ValidatorFunc) -> ValidatorFunc:
        setattr(func, "__validator_fields__", fields)
        setattr(func, "__validator_pre__", pre)
        return func

    return decorator


T = TypeVar("T", bound="BaseModel")


class ModelMeta(type):
    def __new__(mcls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]):
        field_defaults: Dict[str, FieldInfo] = {}
        validators: Dict[str, List[Tuple[ValidatorFunc, bool]]] = {}

        for base in bases:
            field_defaults.update(getattr(base, "__field_defaults__", {}))
            base_validators = getattr(base, "__validators__", {})
            for key, funcs in base_validators.items():
                validators.setdefault(key, []).extend(funcs)

        annotations = namespace.get("__annotations__", {})
        for attr, value in list(namespace.items()):
            if isinstance(value, FieldInfo):
                field_defaults[attr] = value
                namespace.pop(attr)

        for attr, hint in annotations.items():
            if attr in field_defaults:
                continue
            if attr in namespace:
                candidate = namespace[attr]
                if not callable(candidate):
                    field_defaults[attr] = FieldInfo(default=candidate)

        for attr, obj in namespace.items():
            fields = getattr(obj, "__validator_fields__", None)
            if fields:
                pre = bool(getattr(obj, "__validator_pre__", False))
                for field in fields:
                    validators.setdefault(field, []).append((obj, pre))

        namespace["__field_defaults__"] = field_defaults
        namespace["__validators__"] = validators
        return super().__new__(mcls, name, bases, namespace)


class BaseModel(metaclass=ModelMeta):
    __field_defaults__: Dict[str, FieldInfo]
    __validators__: Dict[str, List[Tuple[ValidatorFunc, bool]]]

    def __init__(self, **data: Any) -> None:
        hints = get_type_hints(type(self), include_extras=True)
        for name, hint in hints.items():
            if name.startswith("__"):
                continue
            value = data.get(name, MISSING)
            field_info = self.__field_defaults__.get(name)
            if value is MISSING:
                if field_info is not None:
                    if field_info.default is not MISSING:
                        value = field_info.default
                    elif field_info.default_factory is not None:
                        value = field_info.default_factory()
                if value is MISSING:
                    if self._allows_none(hint):
                        value = None
                    else:
                        raise ValueError(f"Missing required field '{name}' for {type(self).__name__}")
            value = self._apply_validators(name, value, pre=True)
            value = self._coerce_type(name, hint, value)
            value = self._apply_validators(name, value, pre=False)
            setattr(self, name, value)

    @classmethod
    def parse_obj(cls: Type[T], data: Dict[str, Any]) -> T:
        return cls(**data)

    def dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        hints = get_type_hints(type(self), include_extras=True)
        for name in hints:
            value = getattr(self, name)
            result[name] = self._export_value(value)
        return result

    def json(self) -> str:
        return json.dumps(self.dict())

    @classmethod
    def _apply_validators(cls, name: str, value: Any, pre: bool) -> Any:
        for func, is_pre in cls.__validators__.get(name, []):
            if is_pre == pre:
                value = func(cls, value)
        return value

    @classmethod
    def _coerce_type(cls, name: str, hint: Any, value: Any) -> Any:
        origin = get_origin(hint)
        args = get_args(hint)
        if origin is Union and type(None) in args:
            non_none = [arg for arg in args if arg is not type(None)]
            if value is None:
                return None
            target = non_none[0] if non_none else Any
            return cls._coerce_type(name, target, value)
        if origin is Optional:
            inner = args[0]
            if value is None:
                return None
            return cls._coerce_type(name, inner, value)
        if origin is None and hasattr(hint, "__origin__"):
            origin = hint.__origin__  # type: ignore[attr-defined]
            args = getattr(hint, "__args__", ())
        if origin is None:
            literal_args = getattr(hint, "__args__", ()) if getattr(hint, "__origin__", None) is None else ()
            if literal_args:
                return value
        if isinstance(hint, type) and issubclass(hint, BaseModel):
            if isinstance(value, hint):
                return value
            if isinstance(value, dict):
                return hint.parse_obj(value)
        if origin in {list, List, tuple, Tuple} and args:
            return [cls._coerce_type(name, args[0], item) for item in value]
        if origin in {dict, Dict} and len(args) == 2:
            key_type, value_type = args
            return {
                cls._coerce_type(name, key_type, key): cls._coerce_type(name, value_type, val)
                for key, val in value.items()
            }
        return value

    @staticmethod
    def _allows_none(hint: Any) -> bool:
        origin = get_origin(hint)
        args = get_args(hint)
        if origin is Union and type(None) in args:
            return True
        if hint is Optional or hint is Any:
            return True
        if origin is Optional:
            return True
        return False

    @staticmethod
    def _export_value(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.dict()
        if isinstance(value, list):
            return [BaseModel._export_value(v) for v in value]
        if isinstance(value, dict):
            return {k: BaseModel._export_value(v) for k, v in value.items()}
        return value

    @classmethod
    def update_forward_refs(cls, **_: Any) -> None:  # pragma: no cover - compatibility stub
        return None

