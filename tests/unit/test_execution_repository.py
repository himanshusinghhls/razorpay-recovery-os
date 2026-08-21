import pytest

from application.execution.in_memory_repository import (
    InMemoryExecutionRepository,
)
from domain.execution.models import (
    ExecutionStatus,
    RecoveryExecution,
)


def make_execution(
    execution_id="exec_123",
):
    return RecoveryExecution(
        execution_id=execution_id,
        payment_id="pay_test_123",
        action_type="retry_payment",
        status=ExecutionStatus.CREATED,
        external_reference=None,
        message="Execution created",
    )


@pytest.mark.asyncio
async def test_repository_creates_execution():
    repository = InMemoryExecutionRepository()

    execution = make_execution()

    await repository.create(execution)

    result = await repository.get("exec_123")

    assert result == execution


@pytest.mark.asyncio
async def test_repository_updates_execution():
    repository = InMemoryExecutionRepository()

    execution = make_execution()

    await repository.create(execution)

    updated = RecoveryExecution(
        execution_id="exec_123",
        payment_id="pay_test_123",
        action_type="retry_payment",
        status=ExecutionStatus.SUCCEEDED,
        external_reference="order_test_123",
        message="Recovery order created",
    )

    await repository.update(updated)

    result = await repository.get("exec_123")

    assert result == updated


@pytest.mark.asyncio
async def test_repository_rejects_duplicate_execution():
    repository = InMemoryExecutionRepository()

    await repository.create(
        make_execution()
    )

    with pytest.raises(ValueError):
        await repository.create(
            make_execution()
        )


@pytest.mark.asyncio
async def test_repository_returns_none_for_unknown_execution():
    repository = InMemoryExecutionRepository()

    result = await repository.get(
        "does_not_exist"
    )

    assert result is None
