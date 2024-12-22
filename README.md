# datafusion-lldb
LLDB formatters for DataFusion and arrow-rs

> Disclosure: I'm very new to LLDB (I did not use LLDB before doing this repo)
>
> But it was so hard to debug arrow-rs and DataFusion code due to the use of raw data rather than Rust data structures (which is understandable)
>
>  that I decided to create this

the formatted output will hide implementation detail and instead try to show you the value from the user prespective.

Consider this example:
```rust
fn primitive_array() {
    let array = arrow_array::PrimitiveArray::<arrow_array::types::UInt16Type>::from(vec![Some(1), Some(2), None, Some(3), None, Some(67)]);

    println!("{:?}", array); // <-- attach a debugger here, the print is irrelevant
}
```

The output before using this formatters is (when using the RustRover lldb):
```
(lldb) p array
(arrow_array::array::primitive_array::PrimitiveArray<arrow_array::types::UInt16Type>) {
  data_type = {}
  values = {
    buffer = {
      data = strong=1, weak=0 {
        data = {
          ptr = {
            pointer = 0x00006000021fc000
          }
          len = 12
          deallocation = {
            0 = {
              size = 12
              align = (0 = _Align1Shl1)
            }
          }
        }
      }
      ptr = 0x00006000021fc000
      length = 12
    }
    phantom = {}
  }
  nulls = {
    0 = {
      buffer = {
        buffer = {
          data = strong=1, weak=0 {
            data = {
              ptr = {
                pointer = 0x0000000128f04300
              }
              len = 1
              deallocation = {
                0 = {
                  size = 64
                  align = (0 = _Align1Shl6)
                }
              }
            }
          }
          ptr = 0x0000000128f04300
          length = 1
        }
        offset = 0
        len = 6
      }
      null_count = 2
    }
  }
}
```

Which is not really usefull as the actual data is behind that pointers

With the formatter enabled:
```
(lldb) p array
(arrow_array::array::primitive_array::PrimitiveArray<arrow_array::types::UInt16Type>) length=6 {
  [0] = 1
  [1] = 2
  [2] = None
  [3] = 3
  [4] = None
  [5] = 67
}
```


## Limitation

1. A lot is not supported
2. Currently this only work when adding the formatter to the `LLDB` bundled with `RustRover` and when the _LLDB Renderers_ sets to _Bundled renderers_ (I _think_ that RustRover bundled LLDB as it's output is very different than `rust-lldb`)


## Setup
1. Clone this repo
2. Load the `lldb_lookup.py` file, I don't know yet how to enable it automaticlly and not sure if I want to,
   but you can enable it manually like this  
   just run the following in LLDB:
    ```shell
    command script import <path-to-this-repo>/src/lldb/lldb_lookup.py
    ```


## Supported

### Arrow

#### `PrimitiveArray`
`PrimitiveArray` is supported

**Example:** For the following code:
```rust
fn primitive_array() {
    let array = arrow_array::PrimitiveArray::<arrow_array::types::UInt16Type>::from(vec![Some(1), Some(2), None, Some(3), None, Some(67)]);

    println!("{:?}", array); // <-- attach a debugger here, the print is irrelevant
}
```

<details>
<summary>Output difference</summary>

The output before this formatters is (when using the RustRover lldb):
```
(lldb) p array
(arrow_array::array::primitive_array::PrimitiveArray<arrow_array::types::UInt16Type>) {
  data_type = {}
  values = {
    buffer = {
      data = strong=1, weak=0 {
        data = {
          ptr = {
            pointer = 0x00006000021fc000
          }
          len = 12
          deallocation = {
            0 = {
              size = 12
              align = (0 = _Align1Shl1)
            }
          }
        }
      }
      ptr = 0x00006000021fc000
      length = 12
    }
    phantom = {}
  }
  nulls = {
    0 = {
      buffer = {
        buffer = {
          data = strong=1, weak=0 {
            data = {
              ptr = {
                pointer = 0x0000000128f04300
              }
              len = 1
              deallocation = {
                0 = {
                  size = 64
                  align = (0 = _Align1Shl6)
                }
              }
            }
          }
          ptr = 0x0000000128f04300
          length = 1
        }
        offset = 0
        len = 6
      }
      null_count = 2
    }
  }
}
```

With the formatter enabled:
```
(lldb) p array
(arrow_array::array::primitive_array::PrimitiveArray<arrow_array::types::UInt16Type>) length=6 {
  [0] = 1
  [1] = 2
  [2] = None
  [3] = 3
  [4] = None
  [5] = 67
}
```


</details>


#### `BooleanBuffer`

**Example:** For the following code:
```rust
fn boolean_buffer() {
    let array = arrow_buffer::BooleanBuffer::from([true, true, false, true, true, true, true, false, false].as_slice());

    println!("{:?}", array); // <-- attach a debugger here, the print is irrelevant
}
```

<details>
<summary>Output difference</summary>

The output before this formatters is (when using the RustRover lldb):
```
(lldb) p array
(arrow_buffer::buffer::boolean::BooleanBuffer) {
  buffer = {
    data = strong=1, weak=0 {
      data = {
        ptr = {
          pointer = 0x0000000130804300
        }
        len = 2
        deallocation = {
          0 = {
            size = 64
            align = (0 = _Align1Shl6)
          }
        }
      }
    }
    ptr = 0x0000000130804300
    length = 2
  }
  offset = 0
  len = 9
}
```

With the formatter enabled:
```
(lldb) p array
(arrow_buffer::buffer::boolean::BooleanBuffer) length=9 {
  [0] = true
  [1] = true
  [2] = false
  [3] = true
  [4] = true
  [5] = true
  [6] = true
  [7] = false
  [8] = false
}
```


</details>

#### `GenericByteArray<GenericStringType<Offset: OffsetSizeTrait>>`

**Example:** For the following code:
```rust
fn string_array() {
    let array: arrow_array::StringArray = [Some("hello"), Some("hello2"), None, Some("other")].into_iter().collect();

    println!("{:?}", array); // <-- attach a debugger here, the print is irrelevant
}
```

<details>
<summary>Output difference</summary>

The output before this formatters is (when using the RustRover lldb):
```
(lldb) p array
(arrow_array::array::byte_array::GenericByteArray<arrow_array::types::GenericStringType<i32>>) {
  data_type = {}
  value_offsets = {
    0 = {
      buffer = {
        data = strong=1, weak=0 {
          data = {
            ptr = {
              pointer = 0x000000014c804100
            }
            len = 20
            deallocation = {
              0 = {
                size = 64
                align = (0 = _Align1Shl6)
              }
            }
          }
        }
        ptr = 0x000000014c804100
        length = 20
      }
      phantom = {}
    }
  }
  value_data = {
    data = strong=1, weak=0 {
      data = {
        ptr = {
          pointer = 0x000000014d808200
        }
        len = 16
        deallocation = {
          0 = {
            size = 1024
            align = (0 = _Align1Shl6)
          }
        }
      }
    }
    ptr = 0x000000014d808200
    length = 16
  }
  nulls = {
    0 = {
      buffer = {
        buffer = {
          data = strong=1, weak=0 {
            data = {
              ptr = {
                pointer = 0x000000014c804180
              }
              len = 1
              deallocation = {
                0 = {
                  size = 64
                  align = (0 = _Align1Shl6)
                }
              }
            }
          }
          ptr = 0x000000014c804180
          length = 1
        }
        offset = 0
        len = 4
      }
      null_count = 1
    }
  }
}

```

With the formatter enabled:
```
(lldb) p array
(arrow_array::array::byte_array::GenericByteArray<arrow_array::types::GenericStringType<i32>>) length=4 {
  [0] = "hello" {
    0 = "hello" {
      data_ptr = 0x00000001023e8000
      length = 5
    }
  }
  [1] = "hello2" {
    0 = "hello2" {
      data_ptr = 0x00000001023e8020
      length = 6
    }
  }
  [2] = None
  [3] = "other" {
    0 = "other" {
      data_ptr = 0x00000001023e8040
      length = 5
    }
  }
}
```


</details>

#### `GenericByteArray<GenericStringType<Offset: OffsetSizeTrait>>`

**Example:** For the following code:
```rust
fn offset_buffer() {
  let array = {
      let (offset_buffer, ..) = arrow_array::StringArray::from_iter_values(["hello", "hello2"].iter()).into_parts();

      offset_buffer
  };

  println!("{:?}", array); // <-- attach a debugger here, the print is irrelevant
}
```

<details>
<summary>Output difference</summary>

The output before this formatters is (when using the RustRover lldb):
```
(lldb) p array
(arrow_buffer::buffer::offset::OffsetBuffer<i32>) {
  0 = {
    buffer = {
      data = strong=1, weak=0 {
        data = {
          ptr = {
            pointer = 0x0000000135f04300
          }
          len = 12
          deallocation = {
            0 = {
              size = 64
              align = (0 = _Align1Shl6)
            }
          }
        }
      }
      ptr = 0x0000000135f04300
      length = 12
    }
    phantom = {}
  }
}

```

With the formatter enabled:
```
(lldb) p array
(arrow_buffer::buffer::offset::OffsetBuffer<i32>) length=3 {
  [0] = 0
  [1] = 5
  [2] = 11
}
```


</details>

## What can't be supported

### Arrow

#### `dyn Array`/`ArrayRef` in _RustRover LLDB_
Because Rust does not provide type system for LLDB (I think) there is no way to get any data about that array, like what data type or anything basically 

#### `DataType` in _RustRover LLDB_
Because `DataType` is recursive (e.g. Dictionary with key and value fields, wrapped with `Box`) there is currently no way to get any info out of this


------

Help is welcome and appreciated. I hope to add support for more types + normal `rust-lldb` in the future, but no promises