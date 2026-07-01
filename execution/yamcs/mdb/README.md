# YAMCS MDB mount point

The Stage 6.9 candidate does not commit the generated XTCE/MDB file here.

At runtime, Docker Compose mounts the local generated MDB:

    execution/generated/poc_xtce_mdb.xml

into the YAMCS container at:

    /yamcs/mdb/poc_xtce_mdb.xml

Generate the MDB before launching the candidate:

    python3 tools/generate_poc_xtce_mdb.py --opensvf-repo ../opensvf
