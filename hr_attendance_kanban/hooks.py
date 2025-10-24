# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html


def post_init_hook(env):
    # Recompute employee attendance type post install to ensure absent employees get
    # the default absent type
    env.add_to_compute(
        env["hr.employee"]._fields["attendance_type_id"], env["hr.employee"].search([])
    )
