import lldb
import os

def import_file(relative_file_path, module_name):
    import sys
    import importlib.util
    current_folder = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_folder, relative_file_path)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

import_file("lldb_providers.py", "lldb_providers")
import_file("arrow_types.py", "arrow_types")

from lldb_providers import *
from arrow_types import ArrowType, classify_struct, classify_union

def classify_arrow_type(type):
    type_class = type.GetTypeClass()
    if type_class == lldb.eTypeClassStruct:
        return classify_struct(type.name, type.fields)
    if type_class == lldb.eTypeClassUnion:
        return classify_union(type.fields)

    return ArrowType.UNKNOWN

def unwrap_pointers(valobj):
    while valobj.GetType().IsPointerType():
        valobj = valobj.Dereference()
    return valobj

def summary_lookup(valobj, dict):
    # type: (SBValue, dict) -> str
    """Returns the summary provider for the given value"""
    arrow_type = classify_arrow_type(unwrap_pointers(valobj).GetType())

    if arrow_type == ArrowType.PRIMITIVE_ARRAY:
        return LengthSummaryProvider(valobj, dict)

    if arrow_type == ArrowType.BOOLEAN_BUFFER:
        return LengthSummaryProvider(valobj, dict)

    if arrow_type == ArrowType.STRING_ARRAY:
        return LengthSummaryProvider(valobj, dict)

    if arrow_type == ArrowType.OFFSET_BUFFER:
        return LengthSummaryProvider(valobj, dict)

    return ""


def synthetic_lookup(valobj, dict):
    # type: (SBValue, dict) -> object
    """Returns the synthetic provider for the given value"""

    unwrapped = unwrap_pointers(valobj)
    arrow_type = classify_arrow_type(unwrapped.GetType())

    try:
        if arrow_type == ArrowType.PRIMITIVE_ARRAY:
            return ArrowPrimitiveArraySyntheticProvider(valobj, dict)

        if arrow_type == ArrowType.STRING_ARRAY:
            return ArrowStringArraySyntheticProvider(valobj, dict)

        if arrow_type == ArrowType.BOOLEAN_BUFFER:
            return ArrowBooleanBufferSyntheticProvider(valobj, dict)

        if arrow_type == ArrowType.OFFSET_BUFFER:
            return ArrowOffsetBufferSyntheticProvider(valobj, dict)
    except Exception as e:

        # Can have problems with pointers, so try again when the value itself is not
        # a pointer as well
        if unwrapped is not valobj:
            return synthetic_lookup(unwrapped, dict)

        print("Error: ", e)

        raise e

    return DefaultSyntheticProvider(valobj, dict)


def __lldb_init_module(debugger, internal_dict):

    commands = [
        # PrimitiveArray
        'type synthetic add -l lldb_lookup.synthetic_lookup -x "^&*(arrow_array::([a-z_]+::)+)PrimitiveArray<.+>$" --category ArrowRs',
        'type summary add -F lldb_lookup.summary_lookup  -e -x -h "^&*(arrow_array::([a-z_]+::)+)PrimitiveArray<.+>$" --category ArrowRs',

        # StringArray
        'type synthetic add -l lldb_lookup.synthetic_lookup -x "^&*(arrow_array::([a-z_]+::)+)GenericByteArray<.+::GenericStringType<i32>>$" --category ArrowRs',
        'type summary add -F lldb_lookup.summary_lookup  -e -x -h "^&*(arrow_array::([a-z_]+::)+)GenericByteArray<.+::GenericStringType<i32>>$" --category ArrowRs',

        # BooleanBuffer
        'type synthetic add -l lldb_lookup.synthetic_lookup -x "^&*(arrow_buffer::([a-z_]+::)+)BooleanBuffer$" --category ArrowRs',
        'type summary add -F lldb_lookup.summary_lookup  -e -x -h "^&*(arrow_buffer::([a-z_]+::)+)BooleanBuffer$" --category ArrowRs',

        # OffsetBuffer
        'type synthetic add -l lldb_lookup.synthetic_lookup -x "^&*(arrow_buffer::([a-z_]+::)+)OffsetBuffer<.+>$" --category ArrowRs',
        'type summary add -F lldb_lookup.summary_lookup  -e -x -h "^&*(arrow_buffer::([a-z_]+::)+)OffsetBuffer<.+>$" --category ArrowRs',

        # Add here before this
        # also need to add in classify_struct

        'type category enable ArrowRs'

    ]

    for command in commands:
        debugger.HandleCommand(command)
