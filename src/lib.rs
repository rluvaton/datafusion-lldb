
#[cfg(test)]
mod tests {
    use arrow_array::{PrimitiveArray, StringArray};
    use arrow_array::types::{Int32Type, Int8Type, UInt16Type};
    use arrow_buffer::BooleanBuffer;

    #[test]
    fn primitive_array() {
        let array = PrimitiveArray::<UInt16Type>::from(vec![Some(1), Some(2), None, Some(3), None, Some(67)]);

        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", array);
    }

    #[test]
    fn primitive_array_ref() {
        let array = PrimitiveArray::<UInt16Type>::from(vec![Some(1), Some(2), None, Some(3), None, Some(67)]);

        let ref_array = &array;
        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", ref_array);
    }


    #[test]
    fn boolean_buffer() {
        let array = BooleanBuffer::from([true, true, false, true, true, true, true, false, false].as_slice());

        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", array);
    }

    #[test]
    fn string_array() {
        let array: StringArray = [Some("hello"), Some("hello2"), None, Some("other")].into_iter().collect();


        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", array);
    }

    #[test]
    fn ref_string_array() {
        let array: StringArray = [Some("hello"), Some("hello2"), None, Some("other")].into_iter().collect();

        let ref_array = &array;
        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", ref_array);
    }

    #[test]
    fn offset_buffer() {
        let array = {
            let (offset_buffer, ..) = StringArray::from_iter_values(["hello", "hello2"].iter()).into_parts();

            offset_buffer
        };


        // set debugger breakpoint here
        // go to lldb console and type:
        // command script import <repo dir>/src/lldb/lldb_lookup.py
        //
        // then type:
        // p array

        println!("{:?}", array);
    }

}
