"""conversations and messages for the agent layer

Revision ID: 0004_conversations
Revises: 0003_simplify_report_types
Create Date: 2026-04-28

Two tables: conversations (header) and messages (append-only log).
`conversations.agent_key` ties each conversation to a single registered
AgentSpec; subsequent turns always run on the same agent. Tool calls and
tool results are stored as their own message rows so the agent loop can
replay them into the next LLM call.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_conversations"
down_revision: str | None = "0003_simplify_report_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("agent_key", sa.String(64), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_conversations_agent_key", "conversations", ["agent_key"]
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("tool_call_id", sa.String(128)),
        sa.Column("tool_name", sa.String(64)),
        sa.Column("tool_args", postgresql.JSONB()),
        sa.Column("tool_result", postgresql.JSONB()),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_agent_key", table_name="conversations")
    op.drop_table("conversations")
