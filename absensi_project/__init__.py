"""
Inisialisasi absensi_project.

Memastikan kompatibilitas Django dengan Python 3.14+ (CPython commit 5ca4e34).
Pada Python 3.14+, objek `super` dapat disalin (copyable), sehingga `copy(super())`
pada Django < 5.2 menghasilkan objek super alih-alih salinan context.
Patch ini menerapkan perbaikan resmi Django (ticket #35844).
"""

from copy import copy
from django.template import context

def _patch_base_context_copy(self):
    duplicate = context.BaseContext()
    duplicate.__class__ = self.__class__
    duplicate.__dict__ = copy(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate

context.BaseContext.__copy__ = _patch_base_context_copy
