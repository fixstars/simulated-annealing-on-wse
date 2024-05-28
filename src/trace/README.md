# trace

Self-made trace library without simfab. This library can run on real WSE-2.

## Usage

### Settings ( `layout.csl` and `pe_program.csl` )

Internal buffer export settings.

- `layout.csl`

```zig
const tracer_layout = @import_module("trace/tracer_layout.csl");
...
layout {
  ...
  tracer_layout.init();
}
```

- `pe_program.csl`

```zig
const tracer = @import_module("trace/tracer.csl",
    .{ .buffer_size = /* buffer size */ }
);
...
comptime {
  ...
  tracer.export_names();
}
```

### Insert traces (`pe_program.csl`)

`measure(measure_point_id: u16)` function saves the value measure_point_id(u16) and the timestamp ([3]u16).

```zig
fn target_func() void {
  tracer.measure(0);
  // some process...
  tracer.measure(1);
}
```

### Export traces (`run.py`)

```python
def export_traces(runner, width, height):
    def make_u48(words):
        return words[0] + (words[1] << 16) + (words[2] << 32)

    measure_buffer_symbol = runner.get_id('measure_buffer')
    measure_buffer_size =  /* buffer size */
    measure_buffer = np.zeros(height * width * measure_buffer_size, dtype=np.uint32)

    runner.memcpy_d2h(measure_buffer, measure_buffer_symbol, 0, 0, width, height, measure_buffer_size, streaming=False,
                      order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_16BIT, nonblock=False)
    measure_buffer = measure_buffer.reshape((height, width, measure_buffer_size))

    for w in range(width):
        for h in range(height):
            measure_point_buffer = measure_buffer[h, w, 0::4]
            times_buffer = np.array([make_u48(measure_buffer[h, w, i+1:i+4]) for i in range(0, measure_buffer_size, 4)])

            print(f"PE ({w}, {h})")
            print("Trace: ", list(measure_point_buffer))
            print("Trace size :", len(measure_point_buffer))
            print("Times: ", list(times_buffer))
            print("Times size :", len(times_buffer))

```
