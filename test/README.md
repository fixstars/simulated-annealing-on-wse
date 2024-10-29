# generate-testdata.py

Generating uniform random Test Q

# install fixstars amplify
Fixstars amplify is required to obtain optimal E and s for the test data

## amplify token for free
Access https://amplify.fixstars.com/en/register to get token

## install amplify
Install amplify
```sh
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

## Usage example

```sh
python3 test/generate-testdata.py --Num 50 --output test/data50
```

# Test data management with DVC (Fixstars internal user only)

## Install DVC

```sh
pip install dvc[gdrive]
```

## Setup DVC

Please refer to [this link](https://dvc.org/doc/user-guide/data-management/remote-storage/google-drive#using-service-accounts) to get `.json` key file.

```sh
dvc remote modify dataset --local gdrive_service_account_json_file_path path/to/file.json
```

## Check pre-generated data

```console
$ dvc status
...
test/data3000.dvc:
        changed outs:
                not in cache:       test/data3000
...
```

## Download pre-generated data

```console
$ dvc pull test/data3000
Collecting                                                                         ...
A       test/data3000/
1 file added and 3 files fetched
$ dvc status
```

## Upload generated test data

```console
# Generate test data
$ python3 test/generate-testdata.py --Num 50 --output test/data50
# Upload test data
$ dvc add test/data50
$ dvc push test/data50
```
