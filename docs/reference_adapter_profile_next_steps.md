# Reference Adapter Profile — Next Steps

The first Projection Profile candidate is structurally defined and validated.

The next implementation-facing work should proceed in this order:

1. build a profile loader/validator that consumes the candidate YAML and JSON Schema;
2. resolve every `sources[]` reference against the Core Entity Index from the Integration Input Set;
3. implement semantic validation for binding-ID uniqueness and allocation collisions;
4. implement deterministic defaults for C symbols, SRDB names, OpenSVF domain mapping and Core-type projection;
5. emit resolved-value provenance into the Integration Result;
6. replace the current `poc_slice.yaml` consumption path in artifact generation with the candidate Profile + Core Integration Input Set;
7. compare generated `mission_contract.h` and SRDB output against the Stage 6.19 PoC baseline;
8. only after static equivalence, reconnect OpenOBSW/OpenSVF/YAMCS capability-oriented regression paths.

Review-dependent decisions from PoC PR #30 must be incorporated before declaring the schema stable.
