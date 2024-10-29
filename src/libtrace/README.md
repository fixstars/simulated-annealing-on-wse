# libtrace

Self-made trace and collector library without simfab. This library can run on real WSE-2.

## TRACE : Usage

### TRACE : Settings ( `layout.csl` and `pe_program.csl` )

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
  - NOTE
    - Data is dropped if the buffer size is exceeded.
    - If you want to synchronize the cycles in multiple PEs, call `tracer.trace_init()` in advance.

```zig
const tracer = @import_module("trace/tracer.csl",
    .{ .trace_buffer_size = trace_buffer_size }
);
...
comptime {
  ...
  tracer.export_names();
}
```

### TRACE : Insert traces (`pe_program.csl`)

`measure(measure_point_id: u16)` function saves the value measure_point_id(u16) and the timestamp ([3]u16).

```zig
fn target_func() void {
  tracer.measure(0);
  // some process...
  tracer.measure(1);
}
```

### TRACE : Export traces (`run.py`)

```python
def export_traces(runner, width, height):
    def make_u48(words):
        return words[0] + (words[1] << 16) + (words[2] << 32)

    trace_buffer_symbol = runner.get_id('trace_buffer')
    trace_buffer_size =  /* buffer size */
    trace_buffer = np.zeros(height * width * trace_buffer_size, dtype=np.uint32)

    runner.memcpy_d2h(trace_buffer, trace_buffer_symbol, 0, 0, width, height, trace_buffer_size, streaming=False,
                      order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_16BIT, nonblock=False)
    trace_buffer = trace_buffer.reshape((height, width, trace_buffer_size))

    for w in range(width):
        for h in range(height):
            measure_point_buffer = trace_buffer[h, w, 0::4]
            times_buffer = np.array([make_u48(trace_buffer[h, w, i+1:i+4]) for i in range(0, trace_buffer_size, 4)])

            print(f"PE ({w}, {h})")
            print("Trace: ", list(measure_point_buffer))
            print("Trace size :", len(measure_point_buffer))
            print("Times: ", list(times_buffer))
            print("Times size :", len(times_buffer))
```

## COLLECTOR : Usage

### COLLECTOR : Settings ( `layout.csl` and `pe_program.csl` )

Internal buffer export settings.

- `layout.csl`

```zig
const tracer_layout = @import_module("trace/tracer_layout.csl");
...
layout {
  @comptime_assert(collector_buffer_size % tracer_layout.COLLECT_INFO_NUM == 0);
  ...
  tracer_layout.init();
}
```

- `pe_program.csl`
  - NOTE
    - Data is dropped if the buffer size is exceeded.

```zig
const tracer = @import_module("trace/tracer.csl",
    .{ .collector_buffer_size = collector_buffer_size }
);
...
comptime {
  ...
  tracer.export_names();
}
```

### COLLECTOR : Insert statistics (`pe_program.csl`)

`collect(statistics_data: *[COLLECT_INFO_NUM]f32)` function saves the statistics(temperature, energy, do_flip_cnt, current_iteration_num).

```zig
fn save_statistics() void {
    statistics_buf[0] = temperature;
    statistics_buf[1] = min_energy;
    statistics_buf[2] = @bitcast(f32, do_flip_cnt);
    statistics_buf[3] = @bitcast(f32, iter);
    if (tracer.can_collect()) {
      tracer.collect(&statistics_buf);
    }
}
```

### COLLECTOR : Export statistics (`run.py`)

```python
def export_statistics(runner, width):
    def f32_to_u32(x) -> int:
        return struct.unpack('I', struct.pack('f', x))[0]

    collector_buffer_symbol = runner.get_id('collector_buffer')
    collector_buffer_size =  /* buffer size */
    collector_buffer = np.zeros(width * collector_buffer_size, dtype=np.float32)

    runner.memcpy_d2h(collector_buffer, collector_buffer_symbol, 0, 0, width, 1, collector_buffer_size, streaming=False,
                      order=csdk.MemcpyOrder.ROW_MAJOR, data_type=csdk.MemcpyDataType.MEMCPY_32BIT, nonblock=False)
    for x in range(width):
        L = x * collector_buffer_size
        R = (x + 1) * collector_buffer_size
        statistics = collector_buffer[L:R]
        statistics[2::4] = np.vectorize(f32_to_u32)(statistics[2::4])
        statistics[3::4] = np.vectorize(f32_to_u32)(statistics[3::4])
        statistics = statistics.reshape((-1,4))
        print("Statistics: ", list(statistics))
        print("Statistics size : ", len(statistics))
```
