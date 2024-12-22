import sys

import lldb

# Resources
# 1. [Rust LLDB providers](https://github.com/rust-lang/rust/blob/master/src/etc/lldb_providers.py)
# 2. [LLDB Python API](https://lldb.llvm.org/python_api.html)

# from lldb.formatters import Logger

####################################################################################################
# This file contains two kinds of pretty-printers: summary and synthetic.
#
# Important classes from LLDB module:
#   SBValue: the value of a variable, a register, or an expression
#   SBType:  the data type; each SBValue has a corresponding SBType
#
# Summary provider is a function with the type `(SBValue, dict) -> str`.
#   The first parameter is the object encapsulating the actual variable being displayed;
#   The second parameter is an internal support parameter used by LLDB, and you should not touch it.
#
# Synthetic children is the way to provide a children-based representation of the object's value.
# Synthetic provider is a class that implements the following interface:
#
#     class SyntheticChildrenProvider:
#         def __init__(self, SBValue, dict)
#         def num_children(self)
#         def get_child_index(self, str)
#         def get_child_at_index(self, int)
#         def update(self)
#         def has_children(self)
#         def get_value(self)
#
#
# You can find more information and examples here:
#   1. https://lldb.llvm.org/varformats.html
#   2. https://lldb.llvm.org/use/python-reference.html
#   3. https://github.com/llvm/llvm-project/blob/llvmorg-8.0.1/lldb/www/python_reference/lldb.formatters.cpp-pysrc.html
#   4. https://github.com/llvm-mirror/lldb/tree/master/examples/summaries/cocoa
####################################################################################################

PY3 = sys.version_info[0] == 3


class ValueBuilder:
    def __init__(self, valobj):
        # type: (SBValue) -> ValueBuilder
        self.valobj = valobj
        process = valobj.GetProcess()
        self.endianness = process.GetByteOrder()
        self.pointer_size = process.GetAddressByteSize()




def unwrap_unique_or_non_null(unique_or_nonnull):
    # BACKCOMPAT: rust 1.32
    # https://github.com/rust-lang/rust/commit/7a0911528058e87d22ea305695f4047572c5e067
    # BACKCOMPAT: rust 1.60
    # https://github.com/rust-lang/rust/commit/2a91eeac1a2d27dd3de1bf55515d765da20fd86f
    ptr = unique_or_nonnull.GetChildMemberWithName("pointer")
    return ptr if ptr.TypeIsPointerType() else ptr.GetChildAtIndex(0)


class DefaultSyntheticProvider:
    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> DefaultSyntheticProvider
        # logger = Logger.Logger()
        # logger >> "Default synthetic provider for " + str(valobj.GetName())
        self.valobj = valobj

    def num_children(self):
        # type: () -> int
        return self.valobj.GetNumChildren()

    def get_child_index(self, name):
        # type: (str) -> int
        return self.valobj.GetIndexOfChildWithName(name)

    def get_child_at_index(self, index):
        # type: (int) -> SBValue
        return self.valobj.GetChildAtIndex(index)

    def update(self):
        # type: () -> None
        pass

    def has_children(self):
        # type: () -> bool
        return self.valobj.MightHaveChildren()


class EmptySyntheticProvider:
    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> EmptySyntheticProvider
        # logger = Logger.Logger()
        # logger >> "[EmptySyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj

    def num_children(self):
        # type: () -> int
        return 0

    def get_child_index(self, name):
        # type: (str) -> int
        return None

    def get_child_at_index(self, index):
        # type: (int) -> SBValue
        return None

    def update(self):
        # type: () -> None
        pass

    def has_children(self):
        # type: () -> bool
        return False


def LengthSummaryProvider(valobj, dict):
    # type: (SBValue, dict) -> str
    return "length=" + str(valobj.GetNumChildren())


def string_data_slice(value, data_ptr, start_offset, end_offset):
    # type: (SBValue, SBValue, int, int) -> str

    u8_type = get_type_by_name(value, "u8")
    length = end_offset - start_offset
    if length == 0:
        return '""'

    string_data = ""
    for i in range(start_offset, end_offset):
        byte = data_ptr.CreateValueFromAddress(
            "[%s]" % i, data_ptr.GetValueAsUnsigned() + i, u8_type
        ).GetValueAsUnsigned()

        string_data += chr(byte)

    return string_data


def is_bit_on(n, bit):
    return (n & (1 << bit)) != 0

def get_type_by_name(value: lldb.SBValue, typename: str) -> lldb.SBType:
    module = value.GetFrame().GetSymbolContext(lldb.eSymbolContextEverything).GetModule()
    sbtype: lldb.SBType = module.FindFirstType(typename)

    return sbtype

# We then implement a get_type function. We add the option to return a pointer instead of a base type. We can use GetPointerType for this.
def get_type(some_value: lldb.SBValue, typename: str, as_pointer=False) -> lldb.SBType:
    module = some_value.GetFrame().GetSymbolContext(lldb.eSymbolContextEverything).GetModule()
    sbtype: lldb.SBType = module.FindFirstType(typename)
    if as_pointer:
        return sbtype.GetPointerType()
    return sbtype

# User must ensure that the type is an Option type
def is_option_equal_none(option):
    # type: (SBValue) -> bool
    assert option.GetType().GetName().startswith("core::option::Option<")
    return option.GetName().endswith("::None")

def get_option_none(value: lldb.SBValue, index: int, option_type: str):
    return value.CreateValueFromData(f"[{index}]", lldb.SBData(), create_option_none(value, option_type))

def wrap_with_option_some(value: lldb.SBValue) -> lldb.SBValue:
    return value.Cast(create_option_some(value, value.GetType().GetName()))

def create_option_none(value: lldb.SBValue, option_type: str):
    return get_type_by_name(value, f"core::option::Option<{option_type}>::None")

def create_option_some(value: lldb.SBValue, option_type: str):
    return get_type_by_name(value, f"core::option::Option<{option_type}>::Some")

class ScalarBufferParser:
    def __init__(self, valobj, element_type):
        # type: (SBValue) -> ScalarBufferParser
        self.valobj = valobj
        self.element_type = element_type
        self.element_type_size = self.element_type.GetByteSize()

        self.buf = self.valobj.GetChildMemberWithName(
            "buffer"
        )
        self.data_ptr = self.buf.GetChildMemberWithName("ptr")
        self.length = self.buf.GetChildMemberWithName("length").GetValueAsUnsigned() // self.element_type_size

    def get_value_at_index(self, index):
        # type: (int) -> SBValue
        start = self.data_ptr.GetValueAsUnsigned()
        address = start + index * self.element_type_size
        element = self.valobj.GetChildMemberWithName("buffer").CreateValueFromAddress(
            "[%s]" % index, address, self.element_type
        )
        return element

    def get_length(self):
        return self.length

class OffsetBufferParser:
    def __init__(self, valobj, element_type = None):
        # type: (SBValue) -> OffsetBufferParser
        if element_type is None:
            element_type = valobj.GetType().GetTemplateArgumentType(0).GetTypedefedType()

        self.parser = ScalarBufferParser(valobj
                                         # Need to get the ScalarBuffer out of the OffsetBuffer because:
                                         # struct OffsetBuffer<O: ArrowNativeType>(ScalarBuffer<O>)
                                         .GetChildAtIndex(0), element_type)

    def get_value_at_index(self, index):
        # type: (int) -> SBValue
        return self.parser.get_value_at_index(index)

    def get_length(self):
        return self.parser.get_length()


# Parse BooleanBuffer
class BooleanBufferParser:
    def __init__(self, valobj):
        # type: (SBValue) -> BooleanBufferParser
        self.valobj = valobj
        self.u8_type = get_type_by_name(self.valobj, "u8")

        self.length = self.valobj.GetChildMemberWithName("len").GetValueAsUnsigned()

        buffer = self.valobj.GetChildMemberWithName(
            "buffer"
        )
        self.data_ptr = buffer.GetChildMemberWithName("ptr")
        self.offset = buffer.GetChildMemberWithName("offset").GetValueAsUnsigned()


    def get_length(self):
        return self.length

    def get_value_at_index(self, index):
        # type: (int) -> bool
        start = self.data_ptr.GetValueAsUnsigned()
        # because the boolean buffer is bit-packed, we need to calculate the index of the byte
        bit_relative_position = index + self.offset

        # divide by 8 to get the bit position in the byte
        address = start + (bit_relative_position // 8)
        element = self.data_ptr.CreateValueFromAddress(
            "[%s]" % index, address, self.u8_type
        ).GetValueAsUnsigned()

        return is_bit_on(element, bit_relative_position % 8)


class NullBufferParser:
    valueobj: lldb.SBValue
    null_buffer: lldb.SBValue
    _has_nulls: bool
    null_count: int
    boolean_buffer_parser: BooleanBufferParser

    def __init__(self, valobj: lldb.SBValue, is_option: bool = False):
        # type: (SBValue, dict) -> NullBufferParser

        self.valobj = valobj

        self.length = 0
        self._has_nulls = True

        if is_option:
            self._has_nulls = not is_option_equal_none(self.valobj)

        if not self._has_nulls:
            return

        self.null_buffer = self.valobj

        if is_option:
            self.null_buffer = self.valobj.GetChildAtIndex(0)

        # Need to check length of nulls buffer as we might have the nulls be just empty buffer
        self.null_count = self.null_buffer.GetChildMemberWithName("null_count").GetValueAsUnsigned()

        if self.null_count == 0:
            self._has_nulls = False
            return

        # --- Parse BooleanBuffer inside NullBuffer struct -----------
        self.boolean_buffer_parser = BooleanBufferParser(self.null_buffer.GetChildMemberWithName("buffer"))


    def get_length(self):
        return self.null_count

    def has_nulls(self):
        return self._has_nulls

    def is_null(self, index):
        # type: (int) -> bool

        if not self._has_nulls:
            return False

        return not self.boolean_buffer_parser.get_value_at_index(index)


class ArrowBooleanBufferSyntheticProvider:
    """Pretty-printer for arrow_buffer::buffer::boolean::BooleanBuffer

    struct BooleanBuffer { buffer: Buffer, offset: usize, len: usize }
    """

    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> ArrowBooleanBufferSyntheticProvider
        # logger = Logger.Logger()
        # logger >> "[ArrowBooleanBufferSyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj
        self.update()

    def num_children(self):
        # type: () -> int
        return self.parser.get_length()

    def get_child_index(self, name):
        # type: (str) -> int
        index = name.lstrip("[").rstrip("]")
        if index.isdigit():
            return int(index)
        else:
            return -1

    def get_child_at_index(self, index):
        # type: (int) -> SBValue

        val = self.parser.get_value_at_index(index)

        return self.valobj.CreateValueFromExpression( "[%s]" % index, "true" if val else "false")

    def update(self):
        # type: () -> None

        self.parser = BooleanBufferParser(self.valobj)

    def has_children(self):
        # type: () -> bool
        return True

    def get_struct_field_index_by_name(self, struct, name):
        # type: (SBValue, str) -> int
        for i in range(struct.GetNumChildren()):
            if struct.GetChildAtIndex(i).GetName() == name:
                return i
        return -1

    def get_struct_field_by_name(self, struct, name):
        # type: (SBValue, str) -> SBValue
        for i in range(struct.GetNumChildren()):
            child = struct.GetChildAtIndex(i)
            if child.GetName() == name:
                return child
        return None

class ArrowPrimitiveArraySyntheticProvider:
    """Pretty-printer for arrow_array::array::primitive_array::PrimitiveArray<T>

    struct PrimitiveArray<T: ArrowPrimitiveType> { data_type: DataType, values: ScalarBuffer<T::Native>, nulls: Option<NullBuffer> }
    """

    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> ArrowPrimitiveArraySyntheticProvider
        # logger = Logger.Logger()
        # logger >> "[StdVecSyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj
        self.update()

    def num_children(self):
        # type: () -> int
        return self.scalar_buffer_parser.get_length()

    def get_child_index(self, name):
        # type: (str) -> int
        index = name.lstrip("[").rstrip("]")
        if index.isdigit():
            return int(index)
        else:
            return -1

    def get_child_at_index(self, index):
        # type: (int) -> SBValue

        # Check if null

        if self.null_buffer_parser.has_nulls():
            # If has nulls than wrap each value with Some or None
            if self.null_buffer_parser.is_null(index):
                return get_option_none(self.valobj, index, self.element_type.GetName())

            # Until fixing Some, just show the number without Some wrapped
            # return wrap_with_option_some(self.get_value_unchecked(index))
            return self.get_value_unchecked(index)

        return self.get_value_unchecked(index)

    # Get value at index when we know that the index is valid (not null)
    def get_value_unchecked(self, index):
        return self.scalar_buffer_parser.get_value_at_index(index)

    def update(self):
        # type: () -> None

        # Get the native type of the array
        # the native type exists in the PrimitiveArray struct in the field "values" which is a ScalarBuffer
        # And the ScalarBuffer has a generic type which is the native type of the array
        self.element_type = (self.valobj.GetChildMemberWithName("values")
                             .GetType()
                             .GetTemplateArgumentType(0)
                             )


        # When running in IntelliJ, the value for `GetTemplateArgumentType` is Rust code (the type that is passed) but when using rust-lldb it's the actual type
        # So for `arrow_array::array::primitive_array::PrimitiveArray<arrow_array::types::UInt16Type>`, in rust-lldb, `element_type` is `unsigned short`
        # But in IntelliJ, `element_type` is `arrow_array::types::UInt16Type`
        # So we need to align
        if self.element_type.GetTypedefedType().GetByteSize() != 0:
            self.element_type = self.element_type.GetTypedefedType()

        self.scalar_buffer_parser = ScalarBufferParser(self.valobj.GetChildMemberWithName("values"), self.element_type)
        self.null_buffer_parser = NullBufferParser(self.valobj.GetChildMemberWithName("nulls"), is_option=True)

    def has_children(self):
        # type: () -> bool
        return True

    def get_struct_field_index_by_name(self, struct, name):
        # type: (SBValue, str) -> int
        for i in range(struct.GetNumChildren()):
            if struct.GetChildAtIndex(i).GetName() == name:
                return i
        return -1

    def get_struct_field_by_name(self, struct, name):
        # type: (SBValue, str) -> SBValue
        for i in range(struct.GetNumChildren()):
            child = struct.GetChildAtIndex(i)
            if child.GetName() == name:
                return child
        return None

class ArrowOffsetBufferSyntheticProvider:
    """Pretty-printer for arrow_buffer::buffer::offset::OffsetBuffer<T>

    struct OffsetBuffer<O: ArrowNativeType>(ScalarBuffer<O>);
    """

    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> ArrowPrimitiveArraySyntheticProvider
        # logger = Logger.Logger()
        # logger >> "[StdVecSyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj
        self.update()

    def num_children(self):
        # type: () -> int
        return self.parser.get_length()

    def get_child_index(self, name):
        # type: (str) -> int
        index = name.lstrip("[").rstrip("]")
        if index.isdigit():
            return int(index)
        else:
            return -1

    def get_child_at_index(self, index):
        # type: (int) -> SBValue

        return self.parser.get_value_at_index(index)

    def update(self):
        # type: () -> None

        # Get the native type of the array
        # the native type exists in the PrimitiveArray struct in the field "values" which is a ScalarBuffer
        # And the ScalarBuffer has a generic type which is the native type of the array
        self.parser = OffsetBufferParser(self.valobj)

        # sys.stderr.write("self.valobj \n" + str(get_type_by_name(self.valobj, "core::option::Option<i32>::Some(0)")) + "\n")

    def has_children(self):
        # type: () -> bool
        return True

    def get_struct_field_index_by_name(self, struct, name):
        # type: (SBValue, str) -> int
        for i in range(struct.GetNumChildren()):
            if struct.GetChildAtIndex(i).GetName() == name:
                return i
        return -1

    def get_struct_field_by_name(self, struct, name):
        # type: (SBValue, str) -> SBValue
        for i in range(struct.GetNumChildren()):
            child = struct.GetChildAtIndex(i)
            if child.GetName() == name:
                return child
        return None

class ArrowStringArraySyntheticProvider:
    """Pretty-printer for arrow_array::array::byte_array::GenericByteArray<arrow_array::types::GenericStringType<OffsetType>>

    parsing struct GenericByteArray<T: ByteArrayType>

    where the T is GenericStringType<Offset>
    """

    def __init__(self, valobj, dict):
        # type: (SBValue, dict) -> ArrowStringArraySyntheticProvider
        # logger = Logger.Logger()
        # logger >> "[StdVecSyntheticProvider] for " + str(valobj.GetName())
        self.valobj = valobj
        self.update()

    def num_children(self):
        # type: () -> int
        return self.length

    def get_child_index(self, name):
        # type: (str) -> int
        index = name.lstrip("[").rstrip("]")
        if index.isdigit():
            return int(index)
        else:
            return -1

    def get_child_at_index(self, index):
        # type: (int) -> SBValue

        # Check if null

        if self.null_buffer_parser.has_nulls():
            # If has nulls than wrap each value with Some or None
            if self.null_buffer_parser.is_null(index):
                # TODO - change this to output option
                return get_option_none(self.valobj, index, "&str")
            return wrap_with_option_some(self.get_value_unchecked(index))

        return self.get_value_unchecked(index)

    # Get value at index when we know that the index is valid (not null)
    def get_value_unchecked(self, index):
        value_offset_start = self.get_value_offset(index)
        value_offset_end = self.get_value_offset(index + 1)

        string_slice = string_data_slice(self.valobj, self.data_ptr, value_offset_start, value_offset_end)

        # When using rust-lldb providers the debugger does not show the summary of the string (i.e the string itself rather than the length and the pointer)
        # But when using IntelliJ providers it does, I'm not sure why yet...
        return self.valobj.CreateValueFromExpression( "[%s]" % index, '"%s"' % string_slice)


    def get_value_offset(self, index):
        return self.offset_buffer_parser.get_value_at_index(index).GetValueAsUnsigned()


    def update(self):
        # type: () -> None

        self.value_data = self.valobj.GetChildMemberWithName("value_data")
        self.data_ptr = self.value_data.GetChildMemberWithName("ptr")
        self.offset_type = self.get_offset_type()

        self.offset_buffer_parser = OffsetBufferParser(
            self.valobj
            .GetChildMemberWithName("value_offsets"),

            self.offset_type
        )

        # The length of the array is the length of the offsets array - 1 because it's the end index
        self.length = self.offset_buffer_parser.get_length() - 1
        self.null_buffer_parser = NullBufferParser(self.valobj.GetChildMemberWithName("nulls"), is_option=True)

    def has_children(self):
        # type: () -> bool
        return True

    def get_struct_field_index_by_name(self, struct, name):
        # type: (SBValue, str) -> int
        for i in range(struct.GetNumChildren()):
            if struct.GetChildAtIndex(i).GetName() == name:
                return i
        return -1

    def get_struct_field_by_name(self, struct, name):
        # type: (SBValue, str) -> SBValue
        for i in range(struct.GetNumChildren()):
            child = struct.GetChildAtIndex(i)
            if child.GetName() == name:
                return child
        return None

    def get_offset_type(self):
        # type: () -> SBType

        # This should be either i32 (String) or i64 (LargeString)

        # pub struct GenericByteArray<T: ByteArrayType> { ... }
        return (self.valobj.GetType()

                # Get the T: ByteArrayType
                .GetTemplateArgumentType(0)
                # Get the actual type - struct GenericStringType<O: OffsetSizeTrait> { ... }
                .GetTypedefedType()
                # Get the O: OffsetSizeTrait
                .GetTemplateArgumentType(0)
                # Get the actual type - (i32 or i64)
                .GetTypedefedType()
                )
