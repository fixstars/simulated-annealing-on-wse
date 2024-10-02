# Simulated annealing on Cerebras WSE-2
This is a simulated annealing program.
It runs on the Cerebras WSE-2.
## Run on simulator
This program requires the [Cerebras SDK](https://sdk.cerebras.net).
```shell-session
$ command -v cslc cs_python # check SDK
/path/to/cslc
/path/to/cs_python
$ cd path/to/repo
$ ./commands.sh -c config/small.toml
['sdk_debug_shell', 'compile', './layout.csl', '--fabric-dims=15,10', '--fabric-offsets=4,1', '--params=Num:8', '--params=block_height:2', '--params=block_width:2', '--params=grid_height:4', '--params=grid_width:4', '--params=max_iters:32', '--params=T:100', '--params=MEMCPYH2D_DATA_1_ID:0', '--params=MEMCPYD2H_DATA_1_ID:1', '-o=out', '--memcpy', '--channels=1']
out/out.json .json
out/east
out/west
out/generated
out/bin
out/bin/out_0_1.elf .elf
out/bin/out_0_0.elf .elf
out/bin/out_9_0.elf .elf
out/bin/out_8_0.elf .elf
out/bin/out_10_0.elf .elf
out/bin/out_1_0.elf .elf
out/bin/out_4_0.elf .elf
out/bin/out_16_0.elf .elf
out/bin/out_5_0.elf .elf
out/bin/out_2_0.elf .elf
out/bin/out_7_0.elf .elf
out/bin/out_6_0.elf .elf
out/bin/out_14_0.elf .elf
out/bin/out_20_0.elf .elf
out/bin/out_15_0.elf .elf
out/bin/out_17_0.elf .elf
out/bin/out_18_1.elf .elf
out/bin/out_19_0.elf .elf
out/bin/out_18_0.elf .elf
out/bin/out_21_0.elf .elf
out/bin/out_12_1.elf .elf
out/bin/out_3_0.elf .elf
out/bin/out_11_0.elf .elf
out/bin/out_12_0.elf .elf
out/bin/out_13_0.elf .elf
out/bin/out_22_0.elf .elf
out/bin/out_23_0.elf .elf
out/west/bin/out_3_0.elf .elf
out/west/bin/out_1_0.elf .elf
out/west/bin/out_0_0.elf .elf
out/west/bin/out_2_0.elf .elf                                                                                                                                                                                                            out/west/bin/out_5_0.elf .elf
out/west/bin/out_7_0.elf .elf
out/west/bin/out_4_0.elf .elf                                                                                                                                                                                                            out/west/bin/out_6_0.elf .elf
out/east/bin/out_0_0.elf .elf
out/east/bin/out_1_0.elf .elf
out/east/bin/out_2_0.elf .elf
out/east/bin/out_4_0.elf .elf
out/east/bin/out_3_0.elf .elf
out/east/bin/out_5_0.elf .elf
out/west/out.json .json
out/west/bin                                                                                                                                                                                                                             out/east/out.json .json
out/east/bin
Reading file out/out.json
Reading file out/west/out.json
Reading file out/east/out.json
fab w,h = 15,10
Kernel x,y w,h = 4,1 8,8
memcpy x,y w,h = 1,1 13,8
Q=array([[-0.24268414,  0.2758338 , -0.3945537 ,  0.9798639 , -0.11039937,
         0.98718166, -0.18694018,  0.27731764],
       [ 0.2758338 ,  0.8907819 ,  0.23403025,  0.42634422, -0.13989347,
         0.94487214, -0.5499384 ,  0.33648747],
       [-0.3945537 ,  0.23403025,  0.40562558, -0.71141493, -0.7318027 ,
         0.7138331 ,  0.7712871 ,  0.26737833],
       [ 0.9798639 ,  0.42634422, -0.71141493, -0.5439519 ,  0.592214  ,                                                                                                                                                                         -0.78430676, -0.3155741 , -0.92437404],
       [-0.11039937, -0.13989347, -0.7318027 ,  0.592214  , -0.22174606,
        -0.4679598 ,  0.1888378 , -0.6935317 ],
       [ 0.98718166,  0.94487214,  0.7138331 , -0.78430676, -0.4679598 ,
        -0.4626313 ,  0.88123053, -0.8880938 ],
       [-0.18694018, -0.5499384 ,  0.7712871 , -0.3155741 ,  0.1888378 ,
         0.88123053,  0.0400381 ,  0.05279151],
       [ 0.27731764,  0.33648747,  0.26737833, -0.92437404, -0.6935317 ,
        -0.8880938 ,  0.05279151,  0.8204232 ]], dtype=float32)
s_amplify=array([0, 0, 1, 1, 1, 1, 0, 1], dtype=int32)
e_amplify=-3.6303388476371765
params={'Num': '8', 'block_height': '2', 'block_width': '2', 'grid_height': '4', 'grid_width': '4', 'max_iters': '32', 'T': '100', 'MEMCPYH2D_DATA_1_ID': '0', 'MEMCPYD2H_DATA_1_ID': '1'}
runner.load 0.147623755s
runner.run 0.040939392s
memcpy_h2d 0.000471476s
memcpy_d2h 3.093578327s
memcpy_d2h 0.089567749s
runner.stop 1.003578325s
total 4.375759024s
best_s=array([0, 0, 1, 1, 1, 1, 0, 1], dtype=int32)
min_energy=-3.6303388476371765
OK
```

## Run on WSE-2

```shell-session
$ cd path/to/repo
$ python3 test/generate-testdata.py --Num 4096 --output test4096 # generate large data
$ ./commands.sh -r -c ./config/large.toml
```

## License
Please read [LICENSE](LICENSE) and [NOTICE](NOTICE).

