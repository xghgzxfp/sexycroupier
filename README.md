# 世界杯

#### 准备

建议用 `pipenv` (https://docs.pipenv.org/) 管理依赖

    $ brew install pipenv

或

    $ pip install pipenv

安装依赖

    $ cd /path/to/bet_web
    $ pipenv install


#### 启动 app

指定 `FLASK_APP` 以启动 app，指定 `FLASK_DEBUG` 以 debug 模式启动

```
$ FLASK_APP=worldcup/app.py FLASK_DEBUG=1 pipenv run flask run
 * Serving Flask app "worldcup.app"
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

如果需要指定监听的主机或端口，传给 `flask run` 相应的参数

```
$ export FLASK_APP=worldcup/app.py
$ export FLASK_DEBUG=1
$ pipenv run flask run --help
...
Options:
  -h, --host TEXT                 The interface to bind to.
  -p, --port INTEGER              The port to bind to.
  --reload / --no-reload          Enable or disable the reloader.  By default
                                  the reloader is active if debug is enabled.
...
```


#### 增加新依赖

使用 `pipenv` 来安装新依赖，语法接近 `pip`，`pipenv` 会同时更新 `Pipfile` `Pipfile.lock`

    $ pipenv install xxx
    $ pipenv install xxx==1.2.3

#### 进行单元测试

```
$ py.test -v worldcup/test.py
```
