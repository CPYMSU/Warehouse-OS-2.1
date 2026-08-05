"""Add the operational warehouse ledger used by the V2 warehouse pages.

Revision ID: 20260727_0005
Revises: 20260727_0004
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "20260727_0005"
down_revision = "20260727_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE warehouse.item_categories (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          category_code text NOT NULL,
          name text NOT NULL CHECK (length(trim(name)) > 0),
          requires_return boolean NOT NULL DEFAULT false,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, category_code),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE warehouse.items (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          category_id uuid,
          item_code text NOT NULL,
          name text NOT NULL CHECK (length(trim(name)) > 0),
          model text,
          unit text NOT NULL DEFAULT '件',
          safe_quantity numeric(18, 3) NOT NULL DEFAULT 0 CHECK (safe_quantity >= 0),
          unit_price numeric(18, 4),
          supplier_name text,
          critical boolean NOT NULL DEFAULT false,
          perishable boolean NOT NULL DEFAULT false,
          required_storage_condition text,
          default_shelf_life_days integer CHECK (default_shelf_life_days >= 0),
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, item_code),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, category_id)
            REFERENCES warehouse.item_categories(tenant_id, id) ON DELETE RESTRICT
        );
        CREATE INDEX idx_warehouse_items_tenant_name ON warehouse.items(tenant_id, name, active);

        CREATE TABLE warehouse.stock_lots (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          item_id uuid NOT NULL,
          warehouse_id uuid NOT NULL,
          location_id uuid,
          batch_no text,
          production_date date,
          expires_at date,
          quantity_on_hand numeric(18, 3) NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
          quality_status text NOT NULL DEFAULT 'qualified'
            CHECK (quality_status IN ('qualified', 'pending', 'rejected')),
          cold_chain_ok boolean,
          active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, location_id) REFERENCES warehouse.warehouse_locations(tenant_id, id) ON DELETE RESTRICT
        );
        CREATE INDEX idx_stock_lots_tenant_item_stock
          ON warehouse.stock_lots(tenant_id, item_id, warehouse_id, expires_at, created_at)
          WHERE active AND quantity_on_hand > 0;

        CREATE TABLE warehouse.inbound_orders (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          order_no text NOT NULL,
          inbound_type text NOT NULL,
          source_name text,
          warehouse_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'received'
            CHECK (status IN ('pending_review', 'quality_check', 'received', 'cancelled')),
          client_request_id text,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          received_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, order_no),
          UNIQUE (tenant_id, client_request_id),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE warehouse.inbound_order_lines (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          inbound_order_id uuid NOT NULL,
          item_id uuid NOT NULL,
          location_id uuid,
          lot_id uuid,
          quantity numeric(18, 3) NOT NULL CHECK (quantity > 0),
          unit_cost numeric(18, 4),
          batch_no text,
          production_date date,
          expires_at date,
          quality_status text NOT NULL DEFAULT 'qualified'
            CHECK (quality_status IN ('qualified', 'pending', 'rejected')),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, inbound_order_id) REFERENCES warehouse.inbound_orders(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, location_id) REFERENCES warehouse.warehouse_locations(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, lot_id) REFERENCES warehouse.stock_lots(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE warehouse.outbound_orders (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          order_no text NOT NULL,
          use_type text NOT NULL,
          department_name text,
          target_name text,
          urgent boolean NOT NULL DEFAULT false,
          status text NOT NULL DEFAULT 'issued'
            CHECK (status IN ('pending_approval', 'issued', 'cancelled')),
          client_request_id text,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          issued_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, order_no),
          UNIQUE (tenant_id, client_request_id),
          UNIQUE (tenant_id, id)
        );

        CREATE TABLE warehouse.outbound_order_lines (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          outbound_order_id uuid NOT NULL,
          item_id uuid NOT NULL,
          quantity numeric(18, 3) NOT NULL CHECK (quantity > 0),
          unit_cost numeric(18, 4),
          source_warehouse_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, outbound_order_id) REFERENCES warehouse.outbound_orders(tenant_id, id) ON DELETE CASCADE,
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, source_warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TABLE warehouse.loan_returns (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL,
          outbound_line_id uuid NOT NULL,
          expected_return_at timestamptz NOT NULL,
          returned_at timestamptz,
          reminder_status text NOT NULL DEFAULT 'pending'
            CHECK (reminder_status IN ('pending', 'overdue', 'returned')),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, outbound_line_id),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, outbound_line_id)
            REFERENCES warehouse.outbound_order_lines(tenant_id, id) ON DELETE CASCADE
        );

        CREATE TABLE warehouse.shipments (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          shipment_no text NOT NULL,
          item_id uuid NOT NULL,
          source_warehouse_id uuid NOT NULL,
          destination_warehouse_id uuid NOT NULL,
          quantity numeric(18, 3) NOT NULL CHECK (quantity > 0),
          batch_no text,
          expires_at date,
          status text NOT NULL DEFAULT 'in_transit'
            CHECK (status IN ('in_transit', 'arrived', 'cancelled')),
          dispatched_at timestamptz NOT NULL DEFAULT now(),
          eta_at timestamptz,
          arrived_at timestamptz,
          cancelled_at timestamptz,
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, shipment_no),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, source_warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, destination_warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT,
          CHECK (source_warehouse_id <> destination_warehouse_id)
        );

        CREATE TABLE warehouse.stock_ledger (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          item_id uuid NOT NULL,
          lot_id uuid,
          warehouse_id uuid,
          location_id uuid,
          movement_type text NOT NULL CHECK (movement_type IN (
            'inbound', 'outbound', 'transfer_out', 'transfer_in', 'adjustment', 'stocktake'
          )),
          quantity_delta numeric(18, 3) NOT NULL CHECK (quantity_delta <> 0),
          source_type text NOT NULL,
          source_id uuid,
          occurred_at timestamptz NOT NULL DEFAULT now(),
          created_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, lot_id) REFERENCES warehouse.stock_lots(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, warehouse_id) REFERENCES warehouse.warehouses(tenant_id, id) ON DELETE RESTRICT,
          FOREIGN KEY (tenant_id, location_id) REFERENCES warehouse.warehouse_locations(tenant_id, id) ON DELETE RESTRICT
        );
        CREATE INDEX idx_stock_ledger_tenant_item_time
          ON warehouse.stock_ledger(tenant_id, item_id, occurred_at DESC);

        CREATE TABLE warehouse.replenishment_requests (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES iam.tenants(id) ON DELETE CASCADE,
          item_id uuid NOT NULL,
          requested_quantity numeric(18, 3) NOT NULL CHECK (requested_quantity > 0),
          status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'cancelled')),
          requested_by uuid REFERENCES iam.users(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, id),
          FOREIGN KEY (tenant_id, item_id) REFERENCES warehouse.items(tenant_id, id) ON DELETE RESTRICT
        );

        CREATE TRIGGER trg_item_categories_updated BEFORE UPDATE ON warehouse.item_categories FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_items_updated BEFORE UPDATE ON warehouse.items FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_stock_lots_updated BEFORE UPDATE ON warehouse.stock_lots FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_inbound_orders_updated BEFORE UPDATE ON warehouse.inbound_orders FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_outbound_orders_updated BEFORE UPDATE ON warehouse.outbound_orders FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_loan_returns_updated BEFORE UPDATE ON warehouse.loan_returns FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_shipments_updated BEFORE UPDATE ON warehouse.shipments FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER trg_replenishment_requests_updated BEFORE UPDATE ON warehouse.replenishment_requests FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();

        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA warehouse TO warehouse_os;
        ALTER DEFAULT PRIVILEGES IN SCHEMA warehouse GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO warehouse_os;

        DO $$
        DECLARE scoped_table text;
        BEGIN
          FOREACH scoped_table IN ARRAY ARRAY[
            'warehouse.item_categories', 'warehouse.items', 'warehouse.stock_lots',
            'warehouse.inbound_orders', 'warehouse.inbound_order_lines',
            'warehouse.outbound_orders', 'warehouse.outbound_order_lines',
            'warehouse.loan_returns', 'warehouse.shipments', 'warehouse.stock_ledger',
            'warehouse.replenishment_requests'
          ]
          LOOP
            EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', scoped_table);
            EXECUTE format(
              'CREATE POLICY tenant_isolation ON %s USING (tenant_id = app.current_tenant_id()) WITH CHECK (tenant_id = app.current_tenant_id())',
              scoped_table
            );
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS warehouse.replenishment_requests;
        DROP TABLE IF EXISTS warehouse.stock_ledger;
        DROP TABLE IF EXISTS warehouse.shipments;
        DROP TABLE IF EXISTS warehouse.loan_returns;
        DROP TABLE IF EXISTS warehouse.outbound_order_lines;
        DROP TABLE IF EXISTS warehouse.outbound_orders;
        DROP TABLE IF EXISTS warehouse.inbound_order_lines;
        DROP TABLE IF EXISTS warehouse.inbound_orders;
        DROP TABLE IF EXISTS warehouse.stock_lots;
        DROP TABLE IF EXISTS warehouse.items;
        DROP TABLE IF EXISTS warehouse.item_categories;
        """
    )
