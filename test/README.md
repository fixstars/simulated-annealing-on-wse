# generate-testdata.py

Generating uniform random Test Q

# install fixstars amplify
Fixstars amplify is required to obtain optimal E and s for the test data

## amplify token for free
Access https://amplify.fixstars.com/en/register to get token

## install amplify
Install amplify
```shell-session
pip install amplify
```

# args and output
* required args
  * --Num : Size of Q
  * --token : Amplify token. If not specified, used from environment variable: `AMPLIFY_TOKEN`
  * --timeout : timeout to amplify try to solve
  * --output : output directory, default=output
* output
  * output/Q.npy : generated Q array
  * output/s.npy : s array solved by Amplify
  * output/e.npy : min energy solved by Amplify
