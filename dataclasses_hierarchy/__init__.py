"""*Dataclasses-hierarchy: a modern Python 3 interface to particle tracking codes: Zgoubi and MAD-X.*

Zgoubidoo is a Python 3 interface for `Zgoubi`_, a ray-tracing code for beam dynamics simulations. Zgoubido is
intended to follow a modern Python design and aims at being easy to use. Interactive use with iPython or Jupyter
Notebook is supported and encouraged. As such Zgoubidoo can be viewed as a 'Zgoubi for the mere mortal' interface.

More recently, Zgoubidoo learned how to drive MAD-X, in a similar fashion as it runs Zgoubi (via the *georges-core*
library). This is intended to promote more systematic comparisons between the codes (in the few corner cases where it
is possible) and to allow the user to built a complete workflow with a single unified libary: indeed, the optical
design of new machines typically starts with MAD-X for which Zgoubidoo provides a complete interface (survey, Twiss
and tracking modules, as well as the equivalent PTC modules).

Zgoubi
------

Zgoubi is a ray-tracing (tracking) code for beam dynamics simulations. Many magnetic and electric elements are
supported, as well as multiple other features, such as spin tracking. It is maintained by François Méot on SourceForge
(`Zgoubi SourceForge repository`_).

.. _Zgoubi: https://sourceforge.net/projects/zgoubi/
.. _Zgoubi SourceForge repository: https://sourceforge.net/projects/zgoubi/

MAD-X and PTC
-------------

.. _MADX: http://mad.web.cern.ch

Design goals
------------

.. image:: _static/zgoubi_logo.png
   :width: 150 px
   :alt: Zgoubi's logo
   :align: right

- **Fully featured interface to Zgoubi**: all functionalities of Zgoubi are supported through the Python interface;
- **Fully featuted interface to MAD-X and PTC**: all functionalities are supported through the Python interface;
- **Ease of use**: a simple tracking study and its visualization can be set up in just a few lines of code;
- Written in **high-quality Python 3 with type-hints**;
- **Built-in support for multi-core machines**: it is possible and easy to run multiple simulations in parallel and to
  collect the final results;
- The library interface and use-n-feel is **Jupyter notebook friendly**;
- **Decoupling between low-level and high-level use cases**: the low-level support provides a simple Python interface to
  generate Zgoubi (or MAD-X) input files and run the executable while the high-level support provides interfaces with
  more abstraction (`sequences`, etc.);
- Strong support and enforcement of the **systematic use of physical units**: **no units conversion nightmare**, you can
  freely use whatever units set you like, the conversion into Zgoubi's or MAD-X's default units is automatically
  handled.

Publications
------------

- Coming soon.

"""
from __future__ import annotations
import inspect
from types import MethodType
from typing import Optional, Any, Tuple, List, Mapping, Dict, Callable, Protocol
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
    """Protocol for the dataclasses, for static type checks."""
    __dataclass_fields__: Mapping


class ChainedMethod:
    """A descriptor for chained methods calls that propagate up and down the hierarchy.

    Mainly used as a function decorator, mostly for the special __post_init__ method of the dataclasses.
    """
    def __new__(cls, fn: Callable = None, *, finalizer: Callable = None, stop_chain: bool = False):
        """Takes care of the call as a decorator with and without parentheses."""
        def wrap(f):
            return cls(f, finalizer=finalizer, stop_chain=stop_chain)
        if fn is None:
            return wrap
        return super().__new__(cls)

    def __init__(self, fn: Callable = None, *, finalizer: Callable = None, stop_chain: bool = False):
        """

        Args:
            fn: the function to be chained upwards (see documentation)
            finalizer: an optional method to be chained downwards (see documentation)
            stop_chain: a boolean flag to stop the chaining
        """
        self._function: Callable = fn
        self._finalizer_function: Callable = finalizer
        self._stop_chain: bool = stop_chain
        self._name: Optional[str] = None
        self._owner: _Dataclass

    def __set_name__(self, owner: _Dataclass, name: str):
        self._name = name
        self._owner = owner

    def __get__(self, instance: _Dataclass, owner: _Dataclass):
        if instance:
            return MethodType(self, instance)
        return self

    def __call__(self, instance: _Dataclass, *args, **kwargs):
        if self._function is not None:
            _, __ = self._process_arguments(instance, args, kwargs)
            MethodType(self._function, instance)(*_, **__)
        if not self._stop_chain:
            try:
                getattr(super(self._owner, instance), self._name)(*args, **kwargs)
            except AttributeError:
                pass  # Reached a base with no __post_init__, ends the chain
        if self._finalizer_function is not None:
            _, __ = self._process_arguments(instance, args, kwargs)
            MethodType(self._finalizer_function, instance)(*_, **__)

    @property
    def _initvar_fields(self) -> Mapping[str, Any]:
        return {
            k: v.default for k, v in self._owner.__dataclass_fields__.items() if v._field_type.name == '_FIELD_INITVAR'
        }

    def finalizer(self, fn: Callable):
        """Registers the finalizer function."""
        self._finalizer_function = fn
        return self

    def _process_arguments(self, instance: _Dataclass, args: Tuple, kwargs: Mapping) -> Tuple[Tuple, Mapping]:
        if self._name == '__post_init__':
            return self._build_arguments_for_post_init(instance, args)
        else:
            return args, kwargs

    def _build_arguments_for_post_init(self, instance: _Dataclass, args) -> Tuple[Tuple, Dict]:
        """
        When ChainedMethod acts as a descriptor for the special __post_init__ method of the dataclasses, a special
        treatment of the arguments is provided.

        We delegate as much as possible to the dataclasses module, so the initial call to __post_init__ (on the
        created object) is performed by the generated __init__ of the dataclass (automatically created if init=True in
        the definition of the dataclass). The __post_init__ method is called with the collected InitVar fields from
        the whole class hierarchy, in the same order as their definition. This is the standard behavior for the
        dataclasses.

        This means that the __post_init__ method of a given class must know about all the InitVar fields of his parents
        or siblings. This is definitely not practical and it breaks the independance or responsability sharing of the
        classes. The only case where that would be acceptable is if the __post_init__ of a class must explicitely use
        all of them, to override the behavior of the parents.

        The other drawback is that all __post_init__ methods, when chained through the hierarchy, should share the same
        signature. This is not an issue for standard dataclasses, as only a single __post_init__ is called. However,
        when all the calls are chained, this is, once again, not practical.

        Args:
            instance:
            args: the positional arguments prior to the processing (as provided by the __post_init__ call initiated by
            the dataclass' (generated) __init__ method.

        Returns:
            A tuple containing the processed positional arguments and keyword arguments (empty).
        """
        _ = []
        for (k, d), v in zip(self._initvar_fields.items(), args):
            if k in inspect.getfullargspec(self._function).args:
                if v != getattr(instance, k, None) and v != d:
                    _.append(v)
                    continue
                if getattr(instance, k, None) != d:
                    _.append(getattr(instance, k, None))
                    continue
                _.append(d)
        return tuple(_), {}


class DataclassHierarchy(ABCMeta):
    def __new__(mcs: type, name: str, bases: Tuple[DataclassHierarchy, type, ...], dct: Dict[str, Any]):
        a = super().__new__(mcs, name, bases, dct)
        return dataclass(a, repr=True)

    def __init__(cls: _Dataclass, name: str, bases: Tuple[DataclassHierarchy, type, ...], dct: Dict[str, Any]):
        super().__init__(name, bases, dct)

    def __getitem__(cls: _Dataclass, item):
        return cls.__dataclass_fields__[item.rstrip('_')].metadata  # noQA

    def __contains__(cls: _Dataclass, item) -> bool:
        return item in cls.__dataclass_fields__
