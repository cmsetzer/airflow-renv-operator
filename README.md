airflow-renv-operator
=====================

An [Airflow] operator for executing an R script within an [renv] project.

[Airflow]: https://airflow.apache.org
[renv]: https://rstudio.github.io/renv

## Example

Suppose you have an renv project directory like the following:

```
/home/airflow-user/airflow/dags/renv-example
├── .Rprofile
├── renv
│   ├── .gitignore
│   ├── activate.R
│   ├── library
│   ├── local
│   └── settings.dcf
├── renv.lock
└── script.R
```

To configure an Airflow task that activates the renv project and executes `script.R`, use `RenvOperator` like so:

```py
from datetime import datetime, timedelta

from airflow import DAG
from airflow_renv_operator import RenvOperator

dag = DAG(
    dag_id='renv-example-dag',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
)

task = RenvOperator(
    task_id='renv-example-task',
    project_path='/home/airflow-user/airflow/dags/renv-example',
    script_path='/home/airflow-user/airflow/dags/renv-example/script.R',
    dag=dag
)
```

## Usage

To initialize `RenvOperator`, you must supply values for `task_id` and the following required parameters:

* `project_path`: A string or `pathlib.Path` object representing the path to your renv project directory.
* `script_path`: A string or `pathlib.Path` object representing the absolute or relative path to an R script that can be executed within your renv project. If `script_path` is relative, it will be resolved from `project_path`.

Additional parameters accepted by Airflow's [`BaseOperator`] may be passed as keyword arguments.

[`BaseOperator`]: https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/models/index.html#airflow.models.BaseOperator

## Tests

Execute tests with Pytest:

```sh
pytest
```
