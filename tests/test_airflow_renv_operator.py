from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch


def make_subprocess_hook_mock(exit_code: int, output: str) -> Mock:
    """Mock a SubprocessHook factory object for use in testing.

    This mock allows us to validate that the RenvOperator is executing
    subprocess commands as expected without running them for real.
    """
    result_mock = Mock()
    result_mock.exit_code = exit_code
    result_mock.output = output
    hook_instance_mock = Mock()
    hook_instance_mock.run_command = Mock(return_value=result_mock)
    hook_factory_mock = Mock(return_value=hook_instance_mock)
    return hook_factory_mock


@pytest.fixture(scope='function', autouse=True)
def airflow_home(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Set AIRFLOW_HOME to a temp dir while testing.

    This prevents Airflow from initializing in the local directory and
    creating unneeded config files, logs, etc.
    """
    monkeypatch.setenv('AIRFLOW_HOME', str(tmp_path))


@pytest.fixture(scope='function')
def run_command_mock(monkeypatch: MonkeyPatch):
    """Mock a SubprocessHook instance's run_command method."""
    from airflow_renv_operator import SubprocessHook

    original_hook = SubprocessHook
    hook_factory_mock = make_subprocess_hook_mock(0, '[1] Example output from R')
    monkeypatch.setattr('airflow_renv_operator.SubprocessHook', hook_factory_mock)
    yield hook_factory_mock.return_value.run_command
    monkeypatch.setattr('airflow_renv_operator.SubprocessHook', original_hook)


@pytest.fixture(scope='function')
def run_command_mock_with_error(monkeypatch: MonkeyPatch):
    """Mock a SubprocessHook instance's run_command method with an error."""
    from airflow_renv_operator import SubprocessHook

    original_hook = SubprocessHook
    hook_factory_mock = make_subprocess_hook_mock(1, '[1] R raised an error')
    monkeypatch.setattr('airflow_renv_operator.SubprocessHook', hook_factory_mock)
    yield hook_factory_mock.return_value.run_command
    monkeypatch.setattr('airflow_renv_operator.SubprocessHook', original_hook)


@pytest.fixture(scope='session')
def project_path():
    """Provide a project path with a valid renv directory structure."""
    with TemporaryDirectory(prefix='airflow_renv_operator_') as temp_dir:
        temp_dir_path = Path(temp_dir)
        renv_dir = temp_dir_path / 'renv'
        renv_dir.mkdir()
        activate_script = renv_dir / 'activate.R'
        activate_script.touch()
        renv_lock = temp_dir_path / 'renv.lock'
        renv_lock.touch()
        yield temp_dir_path


@pytest.fixture(scope='session')
def project_path_invalid():
    """Provide a project path with an invalid renv directory structure."""
    with TemporaryDirectory(prefix='airflow_renv_operator_') as temp_dir:
        temp_dir_path = Path(temp_dir)
        yield temp_dir_path


@pytest.fixture
def script_path(project_path: Path):
    """Provide a path to an R script in a valid renv directory structure."""
    r_script = project_path / 'script.R'
    r_script.touch()
    return r_script


def test_initialize(project_path: Path, script_path: Path):
    from airflow_renv_operator import RenvOperator

    task = RenvOperator(task_id='test', project_path=project_path, script_path=script_path)
    assert task.project_path == project_path.resolve()
    assert task.script_path == script_path.resolve()


def test_initialize_with_relative_script_path(project_path: Path, script_path: Path):
    from airflow_renv_operator import RenvOperator

    task = RenvOperator(task_id='test', project_path=project_path, script_path=script_path.name)
    assert task.project_path == project_path.resolve()
    assert task.script_path == script_path.resolve()


def test_initialize_from_invalid_project(project_path_invalid: Path, script_path: Path):
    from airflow_renv_operator import RenvOperator

    from airflow import AirflowException

    with pytest.raises(AirflowException, match='Invalid renv project'):
        RenvOperator(task_id='test', project_path=project_path_invalid, script_path=script_path)


def test_execute(project_path: Path, script_path: Path, run_command_mock: Mock):
    from airflow_renv_operator import RenvOperator

    task = RenvOperator(task_id='test', project_path=project_path, script_path=script_path)
    output = task.execute({})

    assert output == '[1] Example output from R'
    run_command_mock.assert_any_call(
        command=['R', '--quiet', '-e', 'renv::restore(clean = TRUE)'],
        cwd=str(project_path.resolve()),
    )
    run_command_mock.assert_called_with(command=['Rscript', str(script_path.resolve())])


def test_execute_with_error(
    project_path: Path, script_path: Path, run_command_mock_with_error: Mock
):
    from airflow_renv_operator import RenvOperator

    from airflow import AirflowException

    with pytest.raises(AirflowException, match=r'R(script)? returned a non-zero exit code'):
        task = RenvOperator(task_id='test', project_path=project_path, script_path=script_path)
        task.execute({})
    assert run_command_mock_with_error.call_count == 1
