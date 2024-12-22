import re


class ArrowType(object):
    UNKNOWN = "Unknown"

    PRIMITIVE_ARRAY = "PrimitiveArray"
    STRING_ARRAY = "StringArray"
    BOOLEAN_BUFFER = "BooleanBuffer"
    OFFSET_BUFFER = "OffsetBuffer"


# Need to also add in __lldb_init_module
PRIMITIVE_ARRAY_REGEX = re.compile(r"^&*(arrow_array::([a-z_]+::)+)PrimitiveArray<.+>$")
STRING_ARRAY_REGEX = re.compile(r"^&*(arrow_array::([a-z_]+::)+)GenericByteArray<.+::GenericStringType<.+>>$")
BOOLEAN_BUFFER_REGEX = re.compile(r"^&*(arrow_buffer::([a-z_]+::)+)BooleanBuffer$")
OFFSET_BUFFER_REGEX = re.compile(r"^&*(arrow_buffer::([a-z_]+::)+)OffsetBuffer<.+>$")

ARROW_TYPE_TO_REGEX = {
    ArrowType.PRIMITIVE_ARRAY: PRIMITIVE_ARRAY_REGEX,
    ArrowType.STRING_ARRAY: STRING_ARRAY_REGEX,
    ArrowType.BOOLEAN_BUFFER: BOOLEAN_BUFFER_REGEX,
    ArrowType.OFFSET_BUFFER: OFFSET_BUFFER_REGEX,
}

def classify_struct(name, fields):
    if len(fields) == 0:
        return ArrowType.UNKNOWN

    for ty, regex in ARROW_TYPE_TO_REGEX.items():
        if regex.match(name):
            return ty

    return ArrowType.UNKNOWN


def classify_union(fields):
    return ArrowType.UNKNOWN
