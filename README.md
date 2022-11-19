# 世界杯

#### 准备

安装依赖

    $ cd /path/to/bet_web
    $ pip install -r requirements.in

增加新的依赖请修改 `requirements.in`


#### 启动 app

指定 `FLASK_APP` 以启动 app，指定 `FLASK_DEBUG` 以 debug 模式启动

```
$ FLASK_APP=worldcup/app.py FLASK_DEBUG=1 flask run
 * Serving Flask app "worldcup.app"
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

如果需要指定监听的主机或端口，传给 `flask run` 相应的参数

```
$ export FLASK_APP=worldcup/app.py
$ export FLASK_DEBUG=1
$ flask run --help
...
Options:
  -h, --host TEXT                 The interface to bind to.
  -p, --port INTEGER              The port to bind to.
  --reload / --no-reload          Enable or disable the reloader.  By default
                                  the reloader is active if debug is enabled.
...
```

可以将常用环境变量写入 `.env` 文件以方便使用

```
$ cat .env
FLASK_APP=worldcup/app.py
FLASK_DEBUG=1
FLASK_SKIP_DOTENV=1
MONGO_URI=mongodb://127.0.0.1:27017
$ flask run
Loading .env environment variables…
 * Serving Flask app "worldcup.app"
 * Forcing debug mode on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
```


#### 常用命令

基于 Flask CLI 实现常用命令，具体实现见 `cli.py`

```
# 插入拍卖记录
$ flask add_auction

# 抓取比赛记录
$ flask fetch_match

# 导入数据
$ flask import_collection

# 归档数据
$ mongoexport --db $DB --collection $CO | tr -d ' ' > history/$DB/$CO.json
```


#### 进行单元测试

```
$ py.test -s -vv worldcup/test.py
```

#### Usecase Diagram

![UseCaseDiagram](https://github.com/xghgzxfp/bet_web/blob/master/Blueprints/UseCase%20Diagram.png "UseCase Diagram")
