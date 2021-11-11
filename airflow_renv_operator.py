from functools import cached_property
import logging
from os import PathLike
from pathlib import Path
from typing import Optional

from airflow.exceptions import AirflowException
from airflow.hooks.subprocess import SubprocessHook
from airflow.models.baseoperator import BaseOperator

logger = logging.getLogger(__name__)


class RenvOperator(BaseOperator):
    """Operator to execute an R script in an renv project.

    Expects a typical renv project directory containing a lockfile
    (renv.lock) and an activate script (renv/activate.R).

    For information on renv, see its documentation:

        https://rstudio.github.io/renv
    """

    def __init__(
        self,
        *,
        project_path: PathLike,
        script_path: PathLike,
        **kwargs: Optional[dict],
    ):
        super().__init__(**kwargs)
        self.project_path = Path(project_path).resolve()
        self.script_path = (self.project_path / Path(script_path)).resolve()

        # Confirm that lockfile exists
        lockfile_path = self.project_path / 'renv.lock'
        activate_path = self.project_path / 'renv/activate.R'
        logger.info(f'Validating renv project: {self.project_path}')
        if not all([lockfile_path.exists(), activate_path.exists()]):
            raise AirflowException(f'Invalid renv project: {self.project_path}')

    @cached_property
    def subprocess_hook(self):
        return SubprocessHook()

    def restore_environment(self) -> None:
        """Restore a project-local environment from renv.lock.

        This ensures the project is in a clean and valid state that
        matches its lockfile.
        """
        logger.info(f'Preparing project-local environment: {self.project_path}')

        # Execute R expression; use --quiet flag to suppress startup message
        r_command = ['R', '--quiet', '-e', 'renv::restore(clean = TRUE)']
        result = self.subprocess_hook.run_command(
            command=r_command,
            cwd=str(self.project_path),
        )
        if result.exit_code != 0:
            raise AirflowException(f'R returned a non-zero exit code: {result.exit_code}')

    def execute(self, context: dict) -> str:
        """Execute the R script in the project-local environment."""
        logger.info(f'Working from project: {self.project_path}')

        # Restore environment to ensure it matches lockfile
        self.restore_environment()

        # Execute script within environment
        logger.info(f'Executing R script in project-local environment: {self.script_path}')
        result = self.subprocess_hook.run_command(command=['Rscript', str(self.script_path)])
        if result.exit_code != 0:
            raise AirflowException(f'Rscript returned a non-zero exit code: {result.exit_code}')
        return result.output
