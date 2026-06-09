from __future__ import annotations

from svf.campaign.procedure import Procedure, ProcedureContext


class A01_PusPingClosedLoopSmoke(Procedure):
    id = "OF-STAGE6-3-PING-SMOKE"
    title = "OrbitFabric PUS ping closed-loop smoke over OpenSVF pipe mode"
    requirement = "OF-STAGE6-3-RUNTIME-SMOKE"

    def run(self, ctx: ProcedureContext) -> None:
        self.step("Send PUS TC(17,1) ping")
        ctx.tc(17, 1, apid=0x001)

        self.step("Expect PUS TM(1,1) acceptance")
        ctx.expect_tm(1, 1, timeout=5.0)

        self.step("Expect PUS TM(17,2) ping reply")
        ctx.expect_tm(17, 2, timeout=5.0)

        self.step("Expect PUS TM(1,7) completion")
        ctx.expect_tm(1, 7, timeout=5.0)
