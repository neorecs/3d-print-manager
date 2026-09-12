"""Link print jobs to the selected Bambu printer.

Revision ID: 0018_print_job_printer
Revises: 0017_bambu_ams_slots
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_print_job_printer"
down_revision = "0017_bambu_ams_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("print_jobs")}
    if "printer_id" not in columns:
        op.add_column("print_jobs", sa.Column("printer_id", sa.Integer(), nullable=True))
    if "bambu_studio_opened_at" not in columns:
        op.add_column("print_jobs", sa.Column("bambu_studio_opened_at", sa.DateTime(timezone=True), nullable=True))
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("print_jobs")
    if not any(item.get("constrained_columns") == ["printer_id"] for item in foreign_keys):
        op.create_foreign_key(
            "fk_print_jobs_printer_id_bambu_printers",
            "print_jobs",
            "bambu_printers",
            ["printer_id"],
            ["id"],
        )


def downgrade() -> None:
    op.drop_constraint("fk_print_jobs_printer_id_bambu_printers", "print_jobs", type_="foreignkey")
    op.drop_column("print_jobs", "bambu_studio_opened_at")
    op.drop_column("print_jobs", "printer_id")
