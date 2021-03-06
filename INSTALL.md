Dependencies
------------

Qiita is a python package, with support for python 2.7, that depends on the following python libraries (all of them can be installed using pip):

<!--
* [pgbouncer](http://pgfoundry.org/projects/pgbouncer)
-->

* [IPython 2.4.1](https://github.com/ipython/ipython)
* [tornado 3.1.1](http://www.tornadoweb.org/en/stable/)
* [toredis](https://pypi.python.org/pypi/toredis)
* [Psycopg2](http://initd.org/psycopg/download/)
* [click](http://click.pocoo.org/)
* [NumPy](https://github.com/numpy/numpy)
* [Pandas >= 0.15](http://pandas.pydata.org/)
* [QIIME 1.8.0-dev](https://github.com/biocore/qiime)
* [future 0.13.0](http://python-future.org/)
* [bcrypt](https://github.com/pyca/bcrypt/)
* [redis](https://github.com/andymccurdy/redis-py)
* [pyparsing 2.0.2](http://pyparsing.wikispaces.com/)
* [networkx](http://networkx.lanl.gov/index.html)
* [WTForms 2.0.1](https://wtforms.readthedocs.org/en/latest/)
* [Mock](http://www.voidspace.org.uk/python/mock/)  For running test code only
* [moi 0.1.0-dev](https://github.com/biocore/mustached-octo-ironman/)

And on the following packages:

* [PostgreSQL 9.3](http://www.postgresql.org/download/)
* [redis-server 2.8.17](http://redis.io)

Install
-------

* Install [PostgreSQL](http://www.postgresql.org/download/) and ensure that your ``$PATH`` environment variable includes the postgres binaries. Do this following the instructions on their website.
* Install [redis](https://pypi.python.org/pypi/redis/). Do this following the instructions on their website.

* Then, install ``qiita-spots`` and it's python dependencies following as follows:

    ```bash
    pip install numpy
pip install https://github.com/biocore/mustached-octo-ironman/archive/master.zip --no-deps
pip install qiita-spots
    ```

After these commands are executed, you will need (1) download a [sample Qiita configuration file](https://raw.githubusercontent.com/biocore/qiita/master/qiita_core/support_files/config_test.txt), this file is included in the `pip` installation, (2) set the `QIITA_CONFIG_FP` environment variable and (3) proceed to initialize your environment:

```bash
# (1) use curl -O if using OS X
wget https://github.com/biocore/qiita/blob/a0628e54aef85b1a064d40d57ca981aaf082a120/qiita_core/support_files/config_test.txt
# (2) set the enviroment variable in your .bashrc
echo "export QIITA_CONFIG_FP=config_test.txt" >> ~/.bashrc
echo "export MOI_CONFIG_FP=$QIITA_CONFIG_FP" >> ~/.bashrc
source ~/.bashrc
# (3) start a test environment
qiita_env make --no-load-ontologies
```

Finally you need to start the server:

```bash
# IPython takes a while to get initialized so wait 30 seconds
qiita_env start_cluster demo test reserved && sleep 30
qiita webserver start

```

If all the above commands executed correctly, you should be able to go to http://localhost:21174 in your browser, to login use `demo@microbio.me` and `password` as the credentials.


## Troubleshooting installation on non-Ubuntu operating systems

### xcode

If running on OS X you should make sure that the Xcode and the Xcode command line tools are installed.

### postgres

If you are using Postgres.app under OSX, a database user will already be created for your username. If you want to use this, you will need to use this identity, change the `USER` and `ADMIN_USER` setting under the `[postgres]` section of your Qiita config file.
