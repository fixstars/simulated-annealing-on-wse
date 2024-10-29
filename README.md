# Simulated annealing on Cerebras WSE-2
This is a simulated annealing program.
It runs on the Cerebras WSE-2.
## Run on simulator
This program requires the [Cerebras SDK](https://sdk.cerebras.net).

```console
$ command -v cslc cs_python # check SDK
/path/to/cslc
/path/to/cs_python
$ cd path/to/repo
$ ./commands.sh -c config/small.toml
['sdk_debug_shell', 'compile', 'src/layout.csl', '--fabric-dims=15,10', '--fabric-offsets=4,1', '--params=Num:8', '--params=block_height:2', '--params=block_width:2', '--params=grid_height:4', '--params=grid_width:4', '--params=trace_buffer_size:0', '--params=collector_buffer_size:0', '--params=enable_simprint:1', '--params=MEMCPYH2D_DATA_1_ID:0', '--params=MEMCPYD2H_DATA_1_ID:1', '-o=out', '--memcpy', '--channels=1', '--max-parallelism=8']
merged_params={'Num': 8, 'block_height': 2, 'block_width': 2, 'grid_height': 4, 'grid_width': 4, 'trace_buffer_size': 0, 'collector_buffer_size': 0, 'enable_simprint': '1', 'MEMCPYH2D_DATA_1_ID': '0', 'MEMCPYD2H_DATA_1_ID': '1', 'max_iters': 128, 'log2_swap_interval': 32, 'time_constant': 2500, 'log_init_temperature': 33357, 'iterations_per_collect': 0, 'suppress_simfab_trace': True}
Q_triu=array([ 0.8051643 , -0.7869472 ,  0.804537  ,  0.3544435 , -0.7616647 ,
        0.3494337 , -0.4819514 ,  0.3152866 ,  0.9003222 , -0.82278615,
        0.5494694 , -0.12901498, -0.4478759 , -0.4408479 , -0.6954764 ,
       -0.5148102 ,  0.5058508 , -0.00116019, -0.6394896 ,  0.54892385,
        0.7363264 , -0.64248747, -0.01411062,  0.11136338, -0.8933897 ,
       -0.37532043,  0.14597186,  0.14320055, -0.0086706 , -0.20689653,
        0.20667265,  0.8402736 , -0.89568305, -0.62131506, -0.8441088 ,
       -0.5168218 ], dtype=float32)
started
runner.load 0.051864831s
runner.run 0.026126865s
init 0.000181472s
Send runtime parameter : max_iters=128 (I)
Send runtime parameter : log2_swap_interval=32 (I)
Send runtime parameter : time_constant=2500 (I)
Send runtime parameter : log_init_temperature=33357 (I)
Send runtime parameter : iterations_per_collect=0 (I)
memcpy_h2d 0.000396088s
swap_temperature 2.5206e-05s
processing: 100%|████████████████| 128/128 [00:06<00:00, 18.73it/s]
memcpy_d2h 6.843572892s
memcpy_d2h 0.024667149s
runner.stop 1.000494296s
total 7.947328799s
best_s=array([1, 1, 0, 1, 1, 0, 1, 1], dtype=int32)
min_energy_wse=-4.348367 (in WSE)
min_energy=-4.348365748301148 (in Python)
opt_s   =  -4.348, [1 1 0 1 1 0 1 1]
best_s  =  -4.348, [1 1 0 1 1 0 1 1]
OK
```

### trace and statistics

```console
$ ./commands.sh -c config/trace_and_statistics.toml
```

```console
$ python3 scripts/analyze_trace.py
The latest log directory already exists.
The latest log file directory : [/home/ubuntu/cerebras_ws/cerebras_sa/log/yyyymmdd-xxxxxx]
Analyze file [y/N]? : y
output directory : /home/ubuntu/cerebras_ws/cerebras_sa
Import trace data...
...
[TIMELINE] Plot PE timeline
[TIMELINE] [1/24] Creating PE(5, 3) timeline...
...
[TIMELINE] [24/24] Creating PE(0, 0) timeline...
[TIMELINE] Writing /home/ubuntu/cerebras_ws/cerebras_sa/timeline.svg...
[TIMELINE] Done
Analyzing pe detail data...
Save PE detail data to /home/ubuntu/cerebras_ws/cerebras_sa/pe_detail.txt
```

```console
$ python3 scripts/analyze_statistics.py
The latest log directory already exists.
The latest log file directory : [/home/ubuntu/cerebras_ws/cerebras_sa/log/yyyymmdd-xxxxxx]
Analyze file [y/N]? : y
output directory : /home/ubuntu/cerebras_ws/cerebras_sa
...
Import statistics data...
...
[PLOT] Plot statistics
===========================
< ALL ITERATION PLOT >
===========================
Creating Tile(0, 0) plot...
Creating Tile(1, 0) plot...
Create svg result file : /home/ubuntu/cerebras_ws/cerebras_sa/statistics_all_iteration.svg
Done
===========================
< ADJUST ITERATION PLOT >
===========================
Creating Tile(0, 0) plot...
Creating Tile(1, 0) plot...
Create svg result file : /home/ubuntu/cerebras_ws/cerebras_sa/statistics.svg
Done
```

- timeline.svg : each pe process timeline
- pe_details.txt : each pe process information
- statistics.svg : simulated annealing information

### parallel tempering

```console
$ python3 test/generate-testdata.py --Num 50 --output test/data50 # generate data (need `AMPLIFY_TOKEN`)
$ ./commands.sh -c config/parallel_tempering.toml
['sdk_debug_shell', 'compile', 'src/layout.csl', '--fabric-dims=15,14', '--fabric-offsets=4,1', '--params=Num:50', '--params=block_height:2', '--params=block_width:2', '--params=grid_height:4', '--params=grid_width:4', '--params=trace_buffer_size:0', '--params=collector_buffer_size:128', '--params=enable_simprint:1', '--params=MEMCPYH2D_DATA_1_ID:0', '--params=MEMCPYD2H_DATA_1_ID:1', '-o=out', '--memcpy', '--channels=1', '--max-parallelism=8']
merged_params={'Num': 50, 'block_height': 2, 'block_width': 2, 'grid_height': 4, 'grid_width': 4, 'trace_buffer_size': 0, 'collector_buffer_size': 128, 'enable_simprint': '1', 'MEMCPYH2D_DATA_1_ID': '0', 'MEMCPYD2H_DATA_1_ID': '1', 'max_iters': 512, 'log2_swap_interval': 5, 'time_constant': 1000, 'log_init_temperature': 32768, 'iterations_per_collect': 8, 'suppress_simfab_trace': True}
Q_triu=array([-0.6297765 , -0.0222319 , -0.54266036, ..., -0.7425307 ,
        0.26843616,  0.78073215], dtype=float32)
started
runner.load 0.078647059s
runner.run 0.037856007s
init 0.000213681s
Send runtime parameter : max_iters=512 (I)
Send runtime parameter : log2_swap_interval=5 (I)
Send runtime parameter : time_constant=1000 (I)
Send runtime parameter : log_init_temperature=32768 (I)
Send runtime parameter : iterations_per_collect=8 (I)
memcpy_h2d 0.000330926s
processing:   6%|█               | 31/512 [00:33<08:47,  1.10s/it]
[i=0/15] swapped 6 pairs
processing:  12%|██              | 63/512 [00:47<05:39,  1.32it/s]
[i=1/15] swapped 2 pairs
processing:  19%|███             | 95/512 [01:01<04:27,  1.56it/s]
[i=2/15] swapped 3 pairs
processing:  25%|████            | 127/512 [01:14<03:46,  1.70it/s]
[i=3/15] swapped 3 pairs
processing:  31%|█████           | 159/512 [01:28<03:15,  1.81it/s]
[i=4/15] swapped 2 pairs
processing:  37%|██████          | 191/512 [01:41<02:50,  1.88it/s]
[i=5/15] swapped 1 pairs
processing:  44%|███████         | 223/512 [01:54<02:29,  1.94it/s]
[i=6/15] swapped 0 pairs
processing:  50%|████████        | 255/512 [02:08<02:09,  1.99it/s]
[i=7/15] swapped 1 pairs
processing:  56%|█████████       | 287/512 [02:22<01:51,  2.02it/s]
[i=8/15] swapped 3 pairs
processing:  62%|██████████      | 319/512 [02:35<01:34,  2.05it/s]
[i=9/15] swapped 1 pairs
processing:  69%|███████████     | 351/512 [02:49<01:17,  2.07it/s]
[i=10/15] swapped 2 pairs
processing:  75%|████████████    | 383/512 [03:03<01:01,  2.09it/s]
[i=11/15] swapped 1 pairs
processing:  81%|█████████████   | 415/512 [03:16<00:45,  2.11it/s]
[i=12/15] swapped 0 pairs
processing:  87%|██████████████  | 447/512 [03:30<00:30,  2.12it/s]
[i=13/15] swapped 0 pairs
processing:  94%|███████████████ | 479/512 [03:44<00:15,  2.14it/s]
[i=14/15] swapped 3 pairs
processing: 100%|████████████████| 511/512 [03:57<00:00,  2.15it/s]
[i=15/15] swapped 1 pairs
processing: 100%|████████████████| 511/512 [03:57<00:00,  2.15it/s]
swap_temperature 237.985667534s
memcpy_d2h 0.50405135s
memcpy_d2h 0.037933778s
Loading traces... Please wait a few minutes.
[COLLECTOR]Detect collector enabled. Loading collector info...
[COLLECTOR]Loading info from the collection row (1/grid_height=4)...
[COLLECTOR]Loading info from the collection row (2/grid_height=4)...
[COLLECTOR]Loading info from the collection row (3/grid_height=4)...
[COLLECTOR]Loading info from the collection row (4/grid_height=4)...
[COLLECTOR]Loading completed.
[COLLECTOR]STATISTICS FILE : /home/ubuntu/cerebras_ws/cerebras_sa/log/yyyymmdd-xxxxxx/statistics.json
Complete load trace (D2H).
SIM_STATS : /home/ubuntu/cerebras_ws/cerebras_sa/log/yyyymmdd-xxxxxx/sim_stats.json
load_trace_and_stop 0.037933778s
total 243.714701108s
best_s=array([1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0,
       1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1,
       1, 1, 1, 0, 1, 1], dtype=int32)
min_energy_wse=-66.581566 (in WSE)
min_energy=-66.58155961334705 (in Python)
opt_s   = -66.582, [1 1 1 0 1 0 1 1 1 0 1 1 0 0 0 1 0 0 1 1 1 0 1 1 1 1 1 0 1 1 0 0 1 1 0 1 0
 0 1 0 1 0 1 1 1 1 1 0 1 1]
best_s  = -66.582, [1 1 1 0 1 0 1 1 1 0 1 1 0 0 0 1 0 0 1 1 1 0 1 1 1 1 1 0 1 1 0 0 1 1 0 1 0
 0 1 0 1 0 1 1 1 1 1 0 1 1]
OK
```

## Run on WSE-2

```console
$ cd path/to/repo
$ python3 test/generate-testdata.py --Num 4096 --output test4096 # generate large data (need `AMPLIFY_TOKEN`)
$ ./commands.sh -r -c ./config/large.toml
```

## License
Please read [LICENSE](LICENSE) and [NOTICE](NOTICE).
