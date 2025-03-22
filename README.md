## Running

You can run script with docker or python

### Python
```shell
python main.py --config_file src/antimagic_field/config_sample.toml
```

### Cmd
```shell
poetry install
poetry run antimagic_field
```

### Docker
```shell
docker build -t AntimagicField .
docker run -it AntimagicField /bin/sh
python main.py
```
