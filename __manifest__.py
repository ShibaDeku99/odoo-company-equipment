{
    "name": "Equipment Management",
    "version": "1.0",
    "author": "ShibaDeku",
    "category": "Human Resources/Equipment",
    "summary": "Quản lý thiết bị công ty",
    "description": """
        Module quản lý thiết bị công ty (Company Equipment).
    """,
    "depends": ["base", "hr", "mail"],
    "data": [
        "security/equipment_security.xml",
        "security/ir.model.access.csv",
        "data/equipment_sequence.xml",
        "views/equipment_views.xml",
        "views/allocation_views.xml",
        "views/return_views.xml",
        "views/maintenance_views.xml",
        "views/liquidation_views.xml",
        "views/equipment_menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
