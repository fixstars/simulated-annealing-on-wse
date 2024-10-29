# config

## Files

|File name| Description|
|---|---|
|large.toml | config file to run large scale ( for run on real WSE )|
|medium_statistics.toml | config file to run in medium statistics mode |
|parallel_tempering.toml | config file to run parallel tempering <br> Please create or download data50 via DVC (see [test/READMe.md](../test/README.md)) |
|small.toml | config file to run small scale ( for run on simulator) |
|trace_and_statistics.toml | config file to run in small trace and statistics mode |
|trace.toml | config file to run in small trace mode |

## Parameters

NOTE: `<name>` should be read as namespace of toml.

- `<params>`.Num : Input size (size of Q)
- `<params>`.block_height : Height of one tile
- `<params>`.block_width : Width of one tile
- `<params>`.grid_height : Number of vertical tiles
- `<params>`.grid_width : Number of horizontal tiles
- `<params>`.max_iters : Maximum number of iterations
- `<params>`.log2_swap_interval : Swap interval of parallel tempering ($I$)
  - ${\rm swap\_interval} = 2^I$
- `<params>`.time_constant : Cooling rate parameter ($K$)
  - $cool\_rate = \exp(-1.0 / K)$
- `<params>`.log_init_temperature : Initial temperature parameter ($C$)
  - $T = \exp((C - 32768) / 256)$
- `<trace.tracer>`.trace_buffer_size : Buffer size in trace mode.
  - Trace mode is disabled in compile time when buffer size is 0.
  - If the trace data exceeds the buffer size, these are dropped.
- `<trace.collector>`.iterations_per_collect : Number of iterations to perform per collection.
- `<trace.collector>`.collector_buffer_size : Buffer size in statistics mode.
  - Statistics mode is disabled in compile time when buffer size is 0.
  - If the statistics data exceeds the buffer size, these are dropped.
  - The buffer size must be a multiple of COLLECT_INFO_NUM(4).
    - COLLECT_INFO : temperature, energy, flip count, current iterations
  - Required buffer size = COLLECT_INFO_NUM(4) * (MAX_ITERS / ITERATIONS_PER_COLLECT)
    - If distributed in a row (block_width), use the following formula to calculate the required buffer size<br>$\lceil \verb|MAX_ITERS| / (\verb|ITERATIONS_PER_COLLECT| \times \verb|BLOCK_WIDTH|) \rceil \times\verb|COLLECT_INFO_NUM|$
- `<sdk>`.suppress_simfab_trace : Suppress output of simfab_trace file when running simulator.
  - If you want to enable tracing with `sdk_debug_shell visualize`, you need to set suppress_simfab_trace to `false`.
- `<test>`.directory : Name of directory where test files are located.
  - test files : `E.npy`, `Q.npy`, `s.npy`
