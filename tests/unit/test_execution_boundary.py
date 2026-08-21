import inspect

from application.execution.executor import RecoveryExecutor
from application.execution.dry_run import DryRunRecoveryExecutor


def test_executor_is_async():
    assert inspect.iscoroutinefunction(
        RecoveryExecutor.execute
    )


def test_dry_run_executor_implements_executor():
    executor = DryRunRecoveryExecutor()

    assert isinstance(executor, RecoveryExecutor)
