from __future__ import annotations
import inspect
from types import MethodType
from typing import Optional, Any, Tuple, Mapping, Dict, Callable, Protocol
from abc import ABCMeta
from dataclasses import dataclass, InitVar

__version__ = "2020.1"

__all__ = [
    'ChainedMethod',
    'DataclassHierarchy',
    'InitVar',
]

InitVar = InitVar


class _Dataclass(Protocol):
    __dataclass_fields__: Mapping


class ChainedMethod:
    def __new__(cls, fn: Callable = None, *, finalizer: Callable = None, stop_chain: bool = False):
        def wrap(f):
            return cls(f, stop_chain)
        if fn is None:
            return wrap
        return super().__new__(cls)

    def __init__(self, fn: Callable = None, *, finalizer: Callable = None, stop_chain: bool = False):
        """

        Args:
            fn:
            stop_chain:
        """
        self._function: Callable = fn
        self._finalizer_function: Callable = finalizer
        self._stop_chain: bool = stop_chain
        self._name: Optional[str] = None
        self._owner: Optional[type] = None

    def __set_name__(self, owner: type, name: str):
        self._name = name
        self._owner = owner

    def __get__(self, instance: _Dataclass, owner: type):
        if instance:
            return MethodType(self, instance)
        return self

    def __call__(self, instance: _Dataclass, *args):
        if self._function is not None:
            MethodType(self._function, instance)(*self._build_arguments_for_post_init(instance, args))
        if self._stop_chain:
            return
        try:
            getattr(super(self._owner, instance), self._name)(*args)
        except AttributeError:
            pass  # Reached a base with no __post_init__, ends the chain
        if self._finalizer_function is not None:
            MethodType(self._finalizer_function, instance)(*self._build_arguments_for_post_init(instance, args))

    def finalizer(self, fn):
        self._finalizer_function = fn

    def _build_arguments_for_post_init(self, instance: _Dataclass, args):
        fields = self._extract_initvar_fields(instance)
        _ = []
        for (k, d), v in zip(fields.items(), args):
            if k in inspect.getfullargspec(self._function).args:
                if v != getattr(instance, k, None) and v != d:
                    _.append(v)
                    continue
                if getattr(instance, k, None) != d:
                    _.append(getattr(instance, k, None))
                    continue
                _.append(d)
        return _

    @staticmethod
    def _extract_initvar_fields(instance: _Dataclass):
        return {
            k: v.default for k, v in instance.__dataclass_fields__.items() if v._field_type.name == '_FIELD_INITVAR'
        }


class DataclassHierarchy(ABCMeta):
    def __new__(mcs: type, name: str, bases: Tuple[DataclassHierarchy, type, ...], dct: Dict[str, Any]):
        a = super().__new__(mcs, name, bases, dct)
        return dataclass(a, repr=True)

    def __init__(cls: DataclassHierarchy, name: str, bases: Tuple[DataclassHierarchy, type, ...], dct: Dict[str, Any]):
        super().__init__(name, bases, dct)

    def __getitem__(cls, item):
        return cls.__dataclass_fields__[item.rstrip('_')].metadata  # noQA

    def __contains__(cls, item) -> bool:
        return item in cls.__dataclass_fields__  # noQA
