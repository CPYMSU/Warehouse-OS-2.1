"""Move the original Civilization demo objects into tenant data.

Revision ID: 20260807_0084
Revises: 20260807_0083
"""

from __future__ import annotations

from alembic import op

revision = "20260807_0084"
down_revision = "20260807_0083"
branch_labels = None
depends_on = None
warehouse_scope = "primary_data"


def upgrade() -> None:
    op.execute(
        """
        WITH seed AS (
          SELECT *
          FROM jsonb_to_recordset(
            $civilization_seed$
            [
              {
                "stable_key": "order-control",
                "domain": "judgement",
                "title": {"zh": "秩序與控制，區別在哪裡？", "en": "Where does order end and control begin?"},
                "prompt": {"zh": "當結構開始替人作決定，秩序是否已經變成控制？", "en": "When structure starts deciding for people, has order already become control?"},
                "thesis": {"zh": "好的秩序減少無意義的摩擦，卻不替人取消判斷。判斷一個系統時，不只看它是否整齊，也看它是否保留退出、質疑與修正的空間。", "en": "Good order reduces meaningless friction without cancelling judgement. Assess a system not only by its neatness, but by whether it preserves room to exit, question and revise."},
                "relations": [{"zh": "組織的記憶", "en": "Organizational memory"}, {"zh": "責任的時間", "en": "The time of responsibility"}],
                "lenses": [
                  {"name": {"zh": "自由的負空間", "en": "Freedom as negative space"}, "text": {"zh": "真正的秩序會主動保留不被安排的部分。", "en": "Real order deliberately leaves some things unarranged."}},
                  {"name": {"zh": "可逆性", "en": "Reversibility"}, "text": {"zh": "一個決定能否被撤回，是秩序與控制的重要分界。", "en": "Whether a decision can be reversed is a key boundary between order and control."}},
                  {"name": {"zh": "最小必要規則", "en": "Minimum necessary rule"}, "text": {"zh": "只建立足以協作的規則，不把可選擇的事變成命令。", "en": "Establish only enough rules for coordination; do not turn choices into commands."}}
                ],
                "occurred_on": "2021-11-01",
                "display_order": 1
              },
              {
                "stable_key": "efficiency-progress",
                "domain": "technology",
                "title": {"zh": "效率一定意味著進步嗎？", "en": "Does efficiency always mean progress?"},
                "prompt": {"zh": "節省下來的時間，最終回到了誰的手中？", "en": "Whose hands receive the time that efficiency saves?"},
                "thesis": {"zh": "效率只是投入與產出的關係，不自動回答方向是否值得。真正的進步還要追問：節省出的時間如何分配，風險轉移給了誰，人的能力是否因此生長。", "en": "Efficiency only describes the relation between input and output; it does not tell us whether the direction is worthwhile. Progress must also ask how saved time is distributed, who receives the risk, and whether human capability grows."},
                "relations": [{"zh": "技術的邊界", "en": "Limits of technology"}, {"zh": "責任的時間", "en": "The time of responsibility"}],
                "lenses": [
                  {"name": {"zh": "分配", "en": "Distribution"}, "text": {"zh": "效率收益是否被共同分享，而不是只被少數節點吸收？", "en": "Are efficiency gains shared, or absorbed by only a few nodes?"}},
                  {"name": {"zh": "反脆弱", "en": "Antifragility"}, "text": {"zh": "高度優化是否消除了系統面對意外所需的冗餘？", "en": "Has optimization removed the redundancy needed to face surprise?"}},
                  {"name": {"zh": "能力生長", "en": "Capability growth"}, "text": {"zh": "工具替代勞動後，人是否獲得了更高層次的判斷能力？", "en": "After tools replace labour, do people gain higher-order judgement?"}}
                ],
                "occurred_on": "2022-05-01",
                "display_order": 2
              },
              {
                "stable_key": "organizational-memory",
                "domain": "organization",
                "title": {"zh": "組織應該記住什麼，又忘記什麼？", "en": "What should an organization remember—and forget?"},
                "prompt": {"zh": "記憶帶來連續性，也可能把過去變成未來的枷鎖。", "en": "Memory creates continuity, but can also turn the past into a constraint on the future."},
                "thesis": {"zh": "組織需要記住決策的理由、證據與責任，卻不應把人的一次錯誤永久固化為身份。好的記憶保存可學習的脈絡，好的遺忘保護重新開始的可能。", "en": "Organizations should remember the reasons, evidence and responsibility behind decisions without permanently turning one mistake into a person's identity. Good memory preserves learnable context; good forgetting protects the possibility of beginning again."},
                "relations": [{"zh": "秩序與控制", "en": "Order and control"}, {"zh": "證據與願望", "en": "Evidence and desire"}],
                "lenses": [
                  {"name": {"zh": "制度記憶", "en": "Institutional memory"}, "text": {"zh": "保存為何如此決定，而不只保存最後結果。", "en": "Preserve why a decision was made, not only its final outcome."}},
                  {"name": {"zh": "人格保護", "en": "Protection of personhood"}, "text": {"zh": "事件可以被審計，人不應被一條記錄永久定義。", "en": "Events can be audited; a person should not be permanently defined by one record."}},
                  {"name": {"zh": "知識半衰期", "en": "Knowledge half-life"}, "text": {"zh": "為每種經驗標注適用條件與失效時間。", "en": "Mark the conditions and expiry horizon of each lesson."}}
                ],
                "occurred_on": "2023-02-01",
                "display_order": 3
              },
              {
                "stable_key": "future-timescale",
                "domain": "time",
                "title": {"zh": "對未來負責，需要多長的時間尺度？", "en": "How long a timescale does responsibility require?"},
                "prompt": {"zh": "季度、任期和一生，會導向完全不同的決定。", "en": "A quarter, a term of office and a lifetime produce very different decisions."},
                "thesis": {"zh": "責任的時間尺度應至少覆蓋決策主要後果的生命週期。當後果超出個人任期，制度就要替尚未到場的人保留發言位置。", "en": "The timescale of responsibility should cover the life cycle of a decision's main consequences. When consequences outlast an individual's term, institutions must preserve a voice for people not yet present."},
                "relations": [{"zh": "效率與進步", "en": "Efficiency and progress"}, {"zh": "技術的邊界", "en": "Limits of technology"}],
                "lenses": [
                  {"name": {"zh": "後果週期", "en": "Consequence cycle"}, "text": {"zh": "不要用預算週期替代事物真正的生命週期。", "en": "Do not substitute budget cycles for the real life cycle of things."}},
                  {"name": {"zh": "未來代表", "en": "Future representation"}, "text": {"zh": "誰在今天的會議裡代表尚未出生的人？", "en": "Who represents people not yet born in today's meeting?"}},
                  {"name": {"zh": "可維護性", "en": "Maintainability"}, "text": {"zh": "把維護成本視為設計本身，而不是留給後人的附註。", "en": "Treat maintenance cost as part of design, not a footnote left to successors."}}
                ],
                "occurred_on": "2024-04-01",
                "display_order": 4
              },
              {
                "stable_key": "evidence-desire",
                "domain": "judgement",
                "title": {"zh": "當證據與願望衝突，如何繼續判斷？", "en": "How do we judge when evidence conflicts with desire?"},
                "prompt": {"zh": "事實不保證舒適，但判斷不能只服務於希望。", "en": "Facts do not guarantee comfort, but judgement cannot serve hope alone."},
                "thesis": {"zh": "先把『我希望如此』與『目前證據支持如此』分開記錄，再尋找能推翻當前結論的新證據。成熟的判斷不是沒有立場，而是允許立場被現實修正。", "en": "Record 'I hope this is true' separately from 'current evidence supports this', then seek evidence capable of overturning the present conclusion. Mature judgement is not positionless; it allows reality to revise the position."},
                "relations": [{"zh": "組織的記憶", "en": "Organizational memory"}, {"zh": "責任的時間", "en": "The time of responsibility"}],
                "lenses": [
                  {"name": {"zh": "可證偽性", "en": "Falsifiability"}, "text": {"zh": "提前寫下什麼證據會讓自己改變看法。", "en": "Write down in advance what evidence would change your view."}},
                  {"name": {"zh": "雙欄記錄", "en": "Two-column record"}, "text": {"zh": "把觀察到的事實與對事實的解釋分開。", "en": "Separate observed facts from interpretations of those facts."}},
                  {"name": {"zh": "反方鋼人", "en": "Steelman the opposition"}, "text": {"zh": "先構造對方最強的論證，再檢查自己的結論。", "en": "Build the strongest opposing argument before checking your conclusion."}}
                ],
                "occurred_on": "2025-01-01",
                "display_order": 5
              },
              {
                "stable_key": "technology-stop",
                "domain": "ethics",
                "title": {"zh": "技術應該在哪裡主動停下來？", "en": "Where should technology choose to stop?"},
                "prompt": {"zh": "能做到，不等於應該做到；可以收集，也不等於值得保留。", "en": "Can does not imply should; collectible does not imply worth retaining."},
                "thesis": {"zh": "技術邊界不只由能力決定，也由尊嚴、可逆性和權力差決定。越難拒絕、越不可撤回、越影響人的核心身份，就越需要主動降低技術的侵入性。", "en": "Technical boundaries are shaped not only by capability, but by dignity, reversibility and power asymmetry. The harder something is to refuse, reverse, or keep away from core identity, the more deliberately technology should reduce its intrusion."},
                "relations": [{"zh": "效率與進步", "en": "Efficiency and progress"}, {"zh": "秩序與控制", "en": "Order and control"}],
                "lenses": [
                  {"name": {"zh": "有意義的同意", "en": "Meaningful consent"}, "text": {"zh": "拒絕是否真的可行，還是只存在於條款文字裡？", "en": "Is refusal genuinely possible, or only present in the terms?"}},
                  {"name": {"zh": "最小收集", "en": "Data minimization"}, "text": {"zh": "沒有明確用途與保存期限的資料，就不應被收集。", "en": "Data without a clear purpose and retention period should not be collected."}},
                  {"name": {"zh": "人類保留權", "en": "Human reserve"}, "text": {"zh": "某些決定應保留由人承擔、解釋與改變的權利。", "en": "Some decisions should preserve the human right to take responsibility, explain and change them."}}
                ],
                "occurred_on": "2026-08-01",
                "display_order": 6
              }
            ]
            $civilization_seed$::jsonb
          ) AS value(
            stable_key text, domain text, title jsonb, prompt jsonb, thesis jsonb,
            relations jsonb, lenses jsonb, occurred_on date, display_order integer
          )
        )
        INSERT INTO civilization.thoughts(
          id, tenant_id, stable_key, domain, title, prompt, thesis, relations,
          lenses, occurred_on, display_order, source
        )
        SELECT gen_random_uuid(), tenant.id, seed.stable_key, seed.domain, seed.title,
               seed.prompt, seed.thesis, seed.relations, seed.lenses,
               seed.occurred_on, seed.display_order, 'seed'
        FROM iam.tenants AS tenant
        CROSS JOIN seed
        WHERE tenant.status = 'active'
        ON CONFLICT (tenant_id, stable_key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM civilization.thoughts
        WHERE source = 'seed'
          AND stable_key IN (
            'order-control', 'efficiency-progress', 'organizational-memory',
            'future-timescale', 'evidence-desire', 'technology-stop'
          )
        """
    )
