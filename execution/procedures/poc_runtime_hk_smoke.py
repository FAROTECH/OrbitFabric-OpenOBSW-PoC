from __future__ import annotations

from svf.campaign.procedure import Procedure, ProcedureContext


class A01_HkTelemetryRuntimeSmoke(Procedure):
    id = "OF-STAGE6-5-HK-SMOKE"
    title = "OrbitFabric HK telemetry runtime smoke over OpenSVF pipe mode"
    requirement = "OF-STAGE6-5-HK-RUNTIME-SMOKE"

    def run(self, ctx: ProcedureContext) -> None:
        self.step("Expect PUS TM(3,25) housekeeping report")
        ctx.expect_tm(3, 25, timeout=15.0)

        self.step("Confirm DHS OBC HK parameter visibility in OpenSVF ParameterStore")
        ctx.wait_until(
            lambda store: (
                store.read("dhs.obc.obt") is not None
                and store.read("dhs.obc.obt").value >= 1.0
            ),
            timeout=10.0,
        )
        ctx.assert_parameter("dhs.obc.obt", greater_than=0.0)
