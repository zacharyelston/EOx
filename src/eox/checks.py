"""Pass/warn/fail bookkeeping shared by every calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Check:
    group: str
    name: str
    value: float
    unit: str
    limit: float | None = None
    op: str = "<="          # value <op> limit must hold
    warn_within: float = 0.0  # PASS becomes WARN when inside this fraction of the limit
    note: str = ""
    warn_limit: float | None = None  # optional second, stricter limit: past it is WARN, past `limit` is FAIL

    def _ok(self, lim: float) -> bool:
        return self.value <= lim if self.op == "<=" else self.value >= lim

    @property
    def status(self) -> str:
        if self.limit is None:
            return "INFO"
        if not self._ok(self.limit):
            return "FAIL"
        if self.warn_limit is not None and not self._ok(self.warn_limit):
            return "WARN"
        if self.warn_within and self.limit:
            margin = (self.limit - self.value) if self.op == "<=" else (self.value - self.limit)
            if margin < self.warn_within * abs(self.limit):
                return "WARN"
        return "PASS"

    def row(self) -> tuple[str, ...]:
        lim = "" if self.limit is None else f"{self.op} {_fmt(self.limit)}"
        if self.warn_limit is not None:
            fail_op = ">" if self.op == "<=" else "<"
            lim = f"{self.op} {_fmt(self.warn_limit)}, fail {fail_op} {_fmt(self.limit)}"
        return (self.status, self.group, self.name, f"{_fmt(self.value)} {self.unit}".strip(), lim, self.note)


def _fmt(x: float) -> str:
    if isinstance(x, str):
        return x
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1000:
        return f"{x:,.0f}"
    if a >= 100:
        return f"{x:.0f}"
    if a >= 10:
        return f"{x:.1f}"
    if a >= 1:
        return f"{x:.2f}"
    return f"{x:.3g}"
