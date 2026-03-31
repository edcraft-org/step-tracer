import textwrap

import pytest

from step_tracer.models import ExecutionContext
from step_tracer.tracer import StepTracer


@pytest.fixture
def tracer() -> StepTracer:
    return StepTracer()


def run(tracer: StepTracer, code: str) -> ExecutionContext:
    dedented = textwrap.dedent(code).strip()
    transformed = tracer.transform_code(dedented)
    return tracer.execute_transformed_code(transformed)
