"""Add domains table

Revision ID: f47e8b9c1d23
Revises: ed37e461f285
Create Date: 2025-09-03 12:00:00.000000

"""

from typing import Sequence, Union
import uuid
import time

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f47e8b9c1d23"
down_revision: Union[str, None] = "64d8cd268d63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create domain table
    op.create_table(
        "domain",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("domain", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )

    # Insert predefined Government of Canada domains
    current_time = int(time.time())

    gov_ca_domains = [
        ("gc.ca", "Government of Canada - Generic"),
        ("parl.gc.ca", "Parliament of Canada"),
        ("canada.ca", "Government of Canada - Main Portal"),
        ("agr.gc.ca", "Agriculture and Agri-Food Canada"),
        ("cbsa-asfc.gc.ca", "Canada Border Services Agency"),
        ("cra-arc.gc.ca", "Canada Revenue Agency"),
        ("dfo-mpo.gc.ca", "Fisheries and Oceans Canada"),
        ("ec.gc.ca", "Environment and Climate Change Canada"),
        ("elections.ca", "Elections Canada"),
        ("esdc-edsc.gc.ca", "Employment and Social Development Canada"),
        ("gac-amc.gc.ca", "Global Affairs Canada"),
        ("hc-sc.gc.ca", "Health Canada"),
        ("ic.gc.ca", "Innovation, Science and Economic Development Canada"),
        ("ircc.gc.ca", "Immigration, Refugees and Citizenship Canada"),
        ("justice.gc.ca", "Department of Justice Canada"),
        ("nrc-cnrc.gc.ca", "National Research Council Canada"),
        ("nrcan-rncan.gc.ca", "Natural Resources Canada"),
        ("phac-aspc.gc.ca", "Public Health Agency of Canada"),
        ("psc-cfp.gc.ca", "Public Service Commission of Canada"),
        ("pwgsc-tpsgc.gc.ca", "Public Works and Government Services Canada"),
        ("rcmp-grc.gc.ca", "Royal Canadian Mounted Police"),
        ("statcan.gc.ca", "Statistics Canada"),
        ("tbs-sct.gc.ca", "Treasury Board of Canada Secretariat"),
        ("tc.gc.ca", "Transport Canada"),
        ("veterans.gc.ca", "Veterans Affairs Canada"),
        ("pc.gc.ca", "Parks Canada"),
        ("csc-scc.gc.ca", "Correctional Service Canada"),
        ("csis-scrs.gc.ca", "Canadian Security Intelligence Service"),
        ("forces.gc.ca", "Canadian Armed Forces"),
        ("ssc-spc.gc.ca", "Shared Services Canada"),
        ("tpsgc-pwgsc.gc.ca", "Public Works and Government Services Canada (French)"),
        ("servicecanada.gc.ca", "Service Canada"),
        ("cic.gc.ca", "Citizenship and Immigration Canada (Legacy)"),
        ("hrsdc-rhdcc.gc.ca", "Human Resources and Skills Development Canada (Legacy)"),
        ("pwgsc.gc.ca", "Public Works and Government Services Canada (Legacy)"),
    ]

    connection = op.get_bind()
    for domain, description in gov_ca_domains:
        connection.execute(
            sa.text(
                "INSERT INTO domain (id, domain, description, created_at, updated_at) "
                "VALUES (:id, :domain, :description, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "domain": domain,
                "description": description,
                "created_at": current_time,
                "updated_at": current_time,
            },
        )


def downgrade():
    op.drop_table("domain")
