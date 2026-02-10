"""Docker-based sandbox execution for step-tracer."""

import json
import subprocess

from step_tracer.models import ExecutionContext


class SandboxExecutionError(Exception):
    """Raised when sandbox execution fails."""

    pass


class SandboxTimeoutError(SandboxExecutionError):
    """Raised when sandbox execution times out."""

    pass


class SandboxExecutor:
    """Executes transformed code in a Docker sandbox."""

    def execute(
        self, transformed_code: str
    ) -> ExecutionContext:
        """
        Execute transformed code in a Docker sandbox.

        Args:
            transformed_code: The transformed Python code to execute

        Returns:
            ExecutionContext with execution trace and variables

        Raises:
            SandboxTimeoutError: If execution exceeds timeout
            SandboxExecutionError: If execution fails
        """
        # Prepare Docker command
        docker_cmd = self._build_docker_command()
        result: subprocess.CompletedProcess[str] | None = None

        try:
            # Run container with transformed code via stdin
            result = subprocess.run(  # noqa: S603
                docker_cmd,
                input=transformed_code,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,  # Don't raise on non-zero exit
            )

            # Parse JSON output
            if result.returncode != 0:
                raise SandboxExecutionError(
                    f"Container exited with code {result.returncode}: {result.stderr}"
                )

            return self._parse_result(result.stdout)

        except subprocess.TimeoutExpired as e:
            raise SandboxTimeoutError(
                "Execution exceeded timeout of 30s"
            ) from e

        except json.JSONDecodeError as e:
            output = result.stdout if result is not None else "(no output)"
            raise SandboxExecutionError(
                f"Failed to parse JSON output: {e}\nOutput: {output}"
            ) from e

    def _build_docker_command(self) -> list[str]:
        """Build Docker command with security restrictions."""
        return [
            "docker",
            "run",
            "--memory",
            "128m",
            "--cpu-quota",
            "50000",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=10m",  # noqa: S108
            "--pids-limit",
            "50",
            "--rm",
            "-i",
            "step-tracer-sandbox:latest",
        ]

    def _parse_result(self, stdout: str) -> ExecutionContext:
        """Parse JSON result and reconstruct ExecutionContext."""
        data = json.loads(stdout)

        if not data["ok"]:
            error = data["error"]
            raise SandboxExecutionError(
                f"{error['type']}: {error['message']}\n{error['traceback']}"
            )

        return ExecutionContext.model_validate(data["execution_context"])
