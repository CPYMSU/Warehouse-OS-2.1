# Industry templates

Warehouse OS 2.1 stores 13 immutable, versioned built-in templates in
`iam.industry_templates`. The complete blueprint is persisted as JSONB and
contains departments, positions, permission sets, navigation defaults, database
access metadata and, for BIU, its public-catalogue metadata.

| Key | Template |
| --- | --- |
| `generic_warehouse` | 通用倉儲 |
| `power_system` | 電力系統 |
| `manufacturing_factory` | 製造工廠 |
| `construction_site` | 建築工程 |
| `restaurant_kitchen` | 餐飲後廚 |
| `medical_clinic` | 醫療診所 |
| `retail_store` | 零售門店 |
| `logistics_express` | 物流快遞 |
| `research_lab` | 實驗室科研 |
| `hotel_homestay` | 酒店民宿 |
| `it_office_asset` | IT 與辦公資產 |
| `film_equipment` | 影視器材 |
| `biu_legal_ethics_case_lab` | BIU 法律倫理學術共同體 |

The legacy `power_grid_uhv` key is deliberately not accepted in this new
catalogue. Use `power_system`.

When the first administrator is created, `bootstrap_admin` records the selected
key on `iam.tenants` and copies its departments and positions to
`iam.organizational_units` and `iam.position_profiles`. Those tenant snapshots
are protected by PostgreSQL RLS. The static catalogue remains global and
read-only to the API role.
