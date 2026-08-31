from __future__ import annotations

from svf.campaign.procedure import Procedure, ProcedureContext


class A01_OrbitFabricPingVerification(Procedure):
    id = "OF-STAGE7-9-PING"
    title = "OrbitFabric-derived OpenOBSW PUS ping verification"
    requirement = "POC-S79-001"

    def run(self, ctx: ProcedureContext) -> None:
        self.step("Send OrbitFabric-mapped PUS TC(17,1)")
        ctx.tc(service=17, subservice=1, apid=0x001)

        self.step("Expect PUS TM(1,1) acceptance")
        ctx.expect_tm(service=1, subservice=1, timeout=5.0)

        self.step("Expect PUS TM(17,2) connection-test report")
        ctx.expect_tm(service=17, subservice=2, timeout=5.0)

        self.step("Expect PUS TM(1,7) completion")
        ctx.expect_tm(service=1, subservice=7, timeout=5.0)
