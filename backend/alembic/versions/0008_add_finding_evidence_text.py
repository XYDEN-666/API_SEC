"""add findings.evidence_text

Persists the scanner's human-readable proof for a finding. Before this the
orchestrator kept only the scanner's own ``Finding.evidence`` string in memory,
so reports and the UI showed the endpoint URL and a finding count instead of
the captured headers/status codes/error excerpts.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("evidence_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "evidence_text")
