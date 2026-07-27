/* ============================================================
   經典版採購入口（只保留安全轉接）

   採購通過／駁回現在必須在 WAREHOUSE OS 2.0 的 Swiss 工作台
   以 Passkey 完成本人蓋章。經典版不得再暴露可直接提交決策的客戶端。
   被退役的舊實作完整保留在 Git 歷史中，供稽核追溯。
   ============================================================ */
(() => {
  const localDevelopment = ["127.0.0.1", "localhost"].includes(window.location.hostname);
  const V2_PROCUREMENT_WORKBENCH_URL = localDevelopment
    ? window.location.origin + "/v2/#/procurement"
    : "https://bonfirework.org/#/procurement";

  const PageProcurement = () => {
    React.useEffect(() => {
      // replace 防止「返回」再次落入已退役的經典採購入口。
      window.location.replace(V2_PROCUREMENT_WORKBENCH_URL);
    }, []);

    return (
      <main className="page procurement-page" aria-busy="true" aria-live="polite">
        <div className="card" style={{ maxWidth: 720, margin: "48px auto", padding: 28 }}>
          <div className="eyebrow">SECURE PROCUREMENT</div>
          <h1 style={{ margin: "8px 0 10px" }}>正在前往採購工作台</h1>
          <p className="muted" style={{ margin: "0 0 18px" }}>
            採購決策已統一移至 Swiss 工作台；通過與駁回都必須使用 Passkey 蓋章。
          </p>
          <a className="btn btn-primary" href={V2_PROCUREMENT_WORKBENCH_URL}>
            立即前往安全採購工作台
          </a>
        </div>
      </main>
    );
  };

  window.PageProcurement = PageProcurement;
})();
