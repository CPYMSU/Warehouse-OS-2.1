"""Shared, versioned research discipline and workflow templates."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

STAGE_STATUSES = frozenset({"planned", "in_progress", "blocked", "completed"})
STAGE_ASSIGNEES = frozenset({"user", "codex", "shared"})
STAGE_TEXT_FIELDS = {"plan": 16000, "findings": 32000, "blockers": 8000, "next_action": 8000}
ARTIFACT_ROLES = frozenset({"design", "dataset", "code", "visualization", "report", "other"})
MAX_STAGE_ARTIFACTS = 40


def normalized_artifacts(value: object) -> list[dict]:
    """Normalize stored references only; the service resolves their project membership."""
    if not isinstance(value, list):
        return []
    result, seen = [], set()
    for item in value[:MAX_STAGE_ARTIFACTS]:
        if not isinstance(item, dict):
            continue
        try:
            version_id = str(UUID(str(item.get("file_version_id") or "")))
        except (ValueError, TypeError, AttributeError):
            continue
        role = item.get("role", "other")
        if not isinstance(role, str) or role not in ARTIFACT_ROLES or version_id in seen:
            continue
        seen.add(version_id)
        result.append({"file_version_id": version_id, "role": role,
                       "title": item.get("title", "")[:200] if isinstance(item.get("title", ""), str) else ""})
    return result


def _step(key: str, title: str, en: str, output: str, prompt: str, workspace: str) -> dict:
    return {"key": key, "title": title, "en": en, "output": output,
            "prompt": prompt, "workspace": workspace}


DISCIPLINES = (
    {
        "key": "data_science", "title": "數據科學", "en": "DATA SCIENCE", "code": "DS",
        "color": "blue", "motto": "從資料中建立可靠的解釋與預測。",
        "summary": "問題與指標 → 資料治理 → 探索 → 建模 → 驗證 → 解釋與應用",
        "stages": [
            _step("question", "確定問題與評估指標", "QUESTION / METRICS", "問題陳述、目標變量、基準與評估指標",
                  "要解釋、預測還是分類什麼？定義研究對象、使用情境、成功標準與研究邊界。", "workflow"),
            _step("database", "收集資料與建立數據庫", "DATA / DATABASE", "版本化資料庫、來源清單與資料字典",
                  "記錄資料來源、授權、樣本、主鍵、時間範圍、變量單位與更新規則；保留原始資料。", "projects"),
            _step("exploration", "清理資料與探索規律", "QUALITY / EXPLORATION", "清理規則、缺失與偏差檢查、探索圖表",
                  "缺失、異常與樣本選擇如何影響結果？哪些規律只是探索發現，還需要獨立樣本驗證？", "projects"),
            _step("design", "設計特徵與模型", "FEATURES / MODEL", "特徵定義、基準模型、資料分割與實驗協議",
                  "按時間或研究單位分割訓練、驗證與測試資料，避免資料洩漏；事先定義比較方法。", "workflow"),
            _step("estimation", "訓練與比較模型", "TRAIN / COMPARE", "固定輸入、參數、日誌與可重跑結果",
                  "比較簡單基準與候選模型，保留隨機種子、軟體環境及每次運算的輸入版本。", "execution"),
            _step("validation", "驗證穩健性與泛化", "VALIDATE / GENERALISE", "樣本外表現、不確定性與敏感性分析",
                  "結果在未見樣本、不同群體及不同設定下是否成立？報告誤差、失敗情境與選模限制。", "execution"),
            _step("interpretation", "解釋結果與適用邊界", "INTERPRET / LIMITS", "變量關係、替代解釋與適用範圍",
                  "哪些關係是預測關聯，哪些有額外的因果識別依據？記錄機制假設、偏差與不可外推的範圍。", "evidence"),
            _step("application", "案例應用與重現發布", "CASE / REPRODUCE", "案例檢驗、版本化論文與重現材料",
                  "用實際案例比較預測與觀察，說明使用條件；整理代碼、資料版本、圖表與研究結論。", "evidence"),
        ],
    },
    {
        "key": "engineering_science", "title": "工程科學", "en": "ENGINEERING SCIENCE", "code": "ES",
        "color": "red", "motto": "讓模型、原型與真實量測彼此校驗。",
        "summary": "需求與限制 → 系統設計 → 建模 → 原型 → 實驗 → 優化 → 案例驗證",
        "stages": [
            _step("requirements", "界定需求與工程限制", "REQUIREMENTS / LIMITS", "性能指標、使用條件、成本與安全邊界",
                  "系統要解決什麼問題？列出可量測的驗收指標、資源、環境、法規與失效限制。", "workflow"),
            _step("architecture", "設計系統與技術路線", "SYSTEM / DESIGN", "系統圖、接口、候選方案與設計取捨",
                  "劃分子系統與接口，對比可行技術路線，記錄材料、尺度及各方案的性能取捨。", "workflow"),
            _step("modelling", "建立理論模型與模擬", "MODEL / SIMULATE", "方程、材料參數、邊界條件與模擬結果",
                  "模型依賴哪些物理假設？檢查單位、守恆關係、數值收斂與邊界條件。", "execution"),
            _step("prototype", "製作原型與實驗方案", "PROTOTYPE / PROTOCOL", "原型版本、實驗設計與量測協議",
                  "固定原型版本、設備設定、控制變量與校準程序；設計能區分候選解釋的實驗。", "workflow"),
            _step("measurement", "實驗量測與資料建庫", "MEASURE / RECORD", "原始量測、校準紀錄、誤差與資料字典",
                  "記錄每次試驗的條件、儀器、樣本與不確定性；保留異常與失敗結果。", "projects"),
            _step("optimisation", "比較結果與迭代優化", "COMPARE / OPTIMISE", "模型偏差、敏感度、優化方案與版本差異",
                  "實測與模擬在哪裡不一致？比較性能、成本與可靠性，記錄每次修改的依據。", "execution"),
            _step("validation", "驗證可靠性與極限", "VALIDATE / FAILURE", "極限工況、可靠性、失效機制與適用邊界",
                  "在不同負載、環境與尺度下檢驗設計，說明安全裕度、失效條件與模型有效範圍。", "evidence"),
            _step("application", "實際案例與工程重現", "CASE / REPRODUCE", "案例報告、設計文件與可重現研究包",
                  "在實際場景對照驗收指標，整理圖紙、代碼、材料與量測資料，使他人能檢查和重做。", "evidence"),
        ],
    },
    {
        "key": "theoretical_science", "title": "理論科學", "en": "THEORETICAL SCIENCE", "code": "TS",
        "color": "ink", "motto": "把概念、假設與推導連成可檢查的論證。",
        "summary": "問題與定義 → 假設 → 形式模型 → 推導 → 反例 → 邊界 → 可檢驗預測",
        "stages": [
            _step("question", "確定理論問題與概念", "QUESTION / DEFINITIONS", "研究問題、概念定義、文獻缺口與範圍",
                  "要解決哪個矛盾、缺口或未解問題？區分定義、已知結果與本研究要提出的新主張。", "workflow"),
            _step("assumptions", "建立公理與基本假設", "AXIOMS / ASSUMPTIONS", "假設清單、符號系統與邏輯依賴",
                  "列明公理、前提與必要條件；說明每個假設的角色、相容性及可能的替代設定。", "workflow"),
            _step("formal_model", "構造形式化模型", "FORMAL MODEL", "數學對象、狀態空間、關係與約束",
                  "把概念轉成明確的對象、變量、方程與約束，說明模型如何對應原始問題。", "projects"),
            _step("derivation", "推導命題與證明", "DERIVE / PROVE", "命題、引理、證明與依賴關係",
                  "逐步寫出推導，不把所需結論當成前提；標示每一步使用的假設和已知結果。", "projects"),
            _step("counterexamples", "檢查反例與一致性", "CHALLENGE / CHECK", "反例搜尋、特殊情況與一致性檢驗",
                  "主動尋找使命題失效的情形；可用符號或數值檢查輔助，但區分計算支持與正式證明。", "execution"),
            _step("boundaries", "分析極限與適用邊界", "LIMITS / DOMAIN", "存在條件、唯一性、極限與失效範圍",
                  "哪些結論依賴特定尺度、參數或正則性？說明存在、唯一性、穩定性及不可推廣的情形。", "evidence"),
            _step("predictions", "提出可檢驗推論", "PREDICT / CONNECT", "可觀測推論、理論比較與案例解釋",
                  "理論帶來哪些新推論？哪些能與資料、實驗或已有案例對照，哪些仍只在形式系統內成立？", "evidence"),
            _step("review", "論證覆核與理論發布", "REVIEW / RELEASE", "可審查論文、證明材料與開放問題",
                  "檢查符號、證明與引用是否完整，明確區分已證命題、猜想與後續研究問題。", "evidence"),
        ],
    },
    {
        "key": "econometrics", "title": "計量經濟學", "en": "ECONOMETRICS", "code": "EC",
        "color": "yellow", "motto": "由資料規律走向經濟機制，再回到真實案例。",
        "summary": "問題 → 數據庫 → 計量模型 → 規律 → 經濟現象 → 假設模型 → 替代關係 → 動態均衡 → 邊界 → 案例",
        "stages": [
            _step("question", "確定研究問題", "QUESTION / ESTIMAND", "問題陳述、研究對象、估計目標與範圍",
                  "要解釋哪個經濟問題？界定研究單位、時間尺度，並區分描述、預測與因果問題。", "workflow"),
            _step("database", "收集數據與建立數據庫", "COLLECT / DATABASE", "來源清單、數據庫、資料字典與樣本規則",
                  "建立觀察單位、主鍵、時間索引、變量定義與單位；記錄缺失、清理、合併及樣本選擇。", "projects"),
            _step("econometric_model", "設計計量模型與識別策略", "SPECIFY / IDENTIFY", "估計方程、變量角色、識別假設與估計方法",
                  "寫出模型、控制項與誤差結構；如要推論因果，交代識別來源、內生性及替代解釋的處理。", "workflow"),
            _step("regularities", "估計模型與發現規律", "ESTIMATE / REGULARITIES", "估計結果、規律圖表、不確定性與穩健性檢查",
                  "哪些方向、幅度、非線性或異質性反覆出現？報告區間、樣本差異與設定敏感性。", "execution"),
            _step("phenomenon", "總結經濟學現象", "ECONOMIC PHENOMENON", "經驗現象、成立情境與競爭性解釋",
                  "把資料中的規律整理成明確的經濟現象；區分觀察到的事實、統計關聯與機制解釋。", "evidence"),
            _step("hypothesis_model", "建立現象的假設模型", "HYPOTHESISE / MODEL", "行為假設、結構方程、內生與外生變量",
                  "提出能產生該現象的行為或制度機制，說明參與者、目標、約束與可反駁的預測。", "workflow"),
            _step("substitution", "分析變量替代與作用關係", "SUBSTITUTION / CHANNELS", "替代或互補關係、彈性、比較靜態與作用通道",
                  "哪些變量可以替代或互補？在其他條件如何固定時，X 的變化經哪些通道影響 Y？寫明符號、方向與假設。", "evidence"),
            _step("dynamic_equilibrium", "研究動態曲線與均衡", "DYNAMICS / EQUILIBRIUM", "動態方程、曲線、均衡點、過渡路徑與穩定性",
                  "刻畫時間、滯後、反饋與調整速度；分析均衡存在條件、衝擊後的路徑及穩定或發散的情形。", "execution"),
            _step("boundaries", "推導影響邏輯與邊界限制", "CAUSAL LOGIC / BOUNDARIES", "影響關係圖、識別條件、參數限制與適用邊界",
                  "哪些影響是模型在指定假設下的推論，哪些已有因果證據？標示可行域、約束、臨界值與不能外推的情境。", "evidence"),
            _step("case_analysis", "結合實際案例分析", "REAL CASE / VALIDATION", "案例背景、模型對照、觀察差異與解釋",
                  "把實際案例的變量、制度與邊界條件代入模型，對照預測和觀察；不能吻合時，記錄需回頭修改的假設。", "evidence"),
            _step("reproduction", "覆核、重現與研究發布", "REVIEW / REPRODUCE", "資料與代碼版本、證據鏈、限制及論文",
                  "整理識別、估計、機制與案例的完整證據鏈；接受覆核，保留失敗結果，發布可檢查的研究版本。", "evidence"),
        ],
    },
)

_BY_KEY = {item["key"]: item for item in DISCIPLINES}
_ALIASES = {name.casefold(): item["key"] for item in DISCIPLINES
            for name in (item["key"], item["title"], item["en"])}
_ALIASES.update({"数据科学": "data_science", "工程科学": "engineering_science",
                 "理论科学": "theoretical_science", "计量经济学": "econometrics"})


def discipline_key(value: object) -> str | None:
    return _ALIASES.get(str(value or "").strip().casefold())


def project_discipline(project: dict) -> str | None:
    metadata = project.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if "research_discipline" in metadata:
        return discipline_key(metadata["research_discipline"])
    return discipline_key(project.get("research_area"))


def discipline_catalogue() -> list[dict]:
    return deepcopy(list(DISCIPLINES))


def discipline_template(key: str | None) -> dict | None:
    return deepcopy(_BY_KEY.get(key))


def discipline_workflow(project: dict, content: dict | None) -> dict:
    key = project_discipline(project)
    template = discipline_template(key)
    content = content if isinstance(content, dict) else {}
    workflows = content.get("discipline_workflows")
    workflows = workflows if isinstance(workflows, dict) else {}
    saved = workflows.get(key)
    saved = saved if isinstance(saved, dict) else {}
    allowed = {stage["key"] for stage in template["stages"]} if template else set()
    stages = {}
    for name, value in saved.items():
        if name not in allowed or not isinstance(value, dict):
            continue
        status = value.get("status")
        stages[name] = {
            "notes": value.get("notes") if isinstance(value.get("notes"), str) else "",
            "status": status if isinstance(status, str) and status in STAGE_STATUSES else "planned",
            "revision": value["revision"] if type(value.get("revision")) is int and value["revision"] >= 0 else 0,
            "updated_at": value.get("updated_at") if isinstance(value.get("updated_at"), str) else None,
            "updated_by": value.get("updated_by") if isinstance(value.get("updated_by"), str) else None,
            **{field: value[field][:limit] if isinstance(value.get(field), str) else ""
               for field, limit in STAGE_TEXT_FIELDS.items()},
            "assignee": value.get("assignee") if isinstance(value.get("assignee"), str) and value["assignee"] in STAGE_ASSIGNEES else "shared",
            "artifacts": normalized_artifacts(value.get("artifacts")),
        }
    return {"discipline": key, "template_version": 1, "stages": stages,
            "total": len(allowed),
            "completed": sum(item.get("status") == "completed" and bool(str(item.get("notes") or "").strip())
                             for item in stages.values()),
            "in_progress": sum(item["status"] == "in_progress" for item in stages.values()),
            "blocked": sum(item["status"] == "blocked" for item in stages.values()),
            "artifact_count": len({artifact["file_version_id"] for item in stages.values() for artifact in item["artifacts"]})}
