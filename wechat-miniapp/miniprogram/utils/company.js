function isWarehouseLinked(company) {
  return Boolean(company && (
    company.warehouse_linked
    || company.mode === 'warehouse_linked'
  ));
}

function modeLabel(company) {
  return isWarehouseLinked(company)
    ? 'Warehouse 2.0 已绑定 · 财务草稿联动'
    : '独立运行';
}

module.exports = { isWarehouseLinked, modeLabel };
