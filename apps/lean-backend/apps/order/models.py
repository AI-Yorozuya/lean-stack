"""訂單管理的資料模型。規則來源：intents/訂單管理.md。

訂單是本 repo 講「狀態與流程」的主場，三拍疊起來：
- 串關聯：訂單 → 客戶（多對一）；明細 → 訂單（1:N）；明細 → 產品（多對一）。
- 抄快照：建單當下把品名＋單價存進明細（見下 snapshot_from）。
- 跑狀態：Order.status 生命週期狀態機（待付款→待出貨→已出貨／已取消）＋鐵則。

教學重點（資料模型＝三問的第一問「有什麼？跟誰有關？」）：
- 三個「東西」＋兩個外部主檔：
    · 訂單 Order、訂單明細 OrderItem（本 app）
    · 客戶 Member（apps/member）＝建單的人；產品 Product（apps/product）＝目錄。

四條設計原則（見 intents/資料模型設計原則.md）落在哪：
- 快照：OrderItem 建單當下把 Product 的品名＋單價「抄一份」（snapshot_from）——
        之後目錄改價/改名/停售，歷史訂單不動。
- 衍生：{明細小計 = 數量 × 單價} → OrderItem.save()；{總額 = 明細加總} → recalc_total()。
- 業務識別碼：order_no（OR-000123）給人對帳，跟 DB 主鍵 pk 分開。
- 停用不刪：客戶/產品都用狀態關閉（各自 app），訂單對客戶/產品用 PROTECT 保住歷史。

其餘鐵則（intents 裡的 {…}）：
- {一張訂單至少一筆明細}     → 建立/修改入口（apis.py）擋。
- {已出貨後明細/總額不可改}  → Order.is_editable（EDITABLE_STATUSES），update 入口擋。
- {終態不可再轉}/{跳步不可轉} → Order.apply_transition() 用 TRANSITIONS 表守。

為什麼鐵則寫在 model / 入口，而不是「相信前端」？
前端可以算給人看（體驗），但**真相必須由後端算/擋**——承重牆砌在後端才擋得住改 request。
"""
from decimal import Decimal

from django.db import models

from apps._common.models import TimeStampedModel


class TransitionError(Exception):
    """狀態機擋下來的「非法轉移」（終態不可轉、跳步不可轉）。API 層轉成 422。"""


class Order(TimeStampedModel):
    """一次銷售：串客戶＋明細（含快照），再由 status 生命週期狀態機管流程。"""

    class Status(models.TextChoices):
        # value（存 DB / 走 API）  , label（給人看的中文）
        PENDING = 'PENDING', '待付款'
        AWAITING = 'AWAITING', '待出貨'      # 已收款、等出貨
        SHIPPED = 'SHIPPED', '已出貨'        # 終態：成功
        CANCELLED = 'CANCELLED', '已取消'    # 終態：作廢

    # ── 狀態機的「真相」：合法轉移表。action → 從哪些狀態、轉去哪、動詞。──
    # 沒列在這裡的 (狀態, 動作) 組合＝非法（含終態不可轉、跳步不可轉）。
    TRANSITIONS = {
        'pay':    {'from': (Status.PENDING,),                  'to': Status.AWAITING,  'verb': '收款'},
        'ship':   {'from': (Status.AWAITING,),                 'to': Status.SHIPPED,   'verb': '出貨'},
        'cancel': {'from': (Status.PENDING, Status.AWAITING),  'to': Status.CANCELLED, 'verb': '取消'},
    }
    # 鐵則 {已收款後明細/總額不可改}：只有待付款（未收款）能動明細。
    # 收款後鎖定——否則改了總額但錢已收，帳會脫鉤（已收款訂單改小→負淨額→作廢會吞掉客戶溢繳）。
    EDITABLE_STATUSES = (Status.PENDING,)

    # 業務識別碼（單號）≠ DB 主鍵：對外對帳看 order_no，pk 是內部的事。
    # 建立時自動從 pk 衍生（見 save()）；unique 保證不撞。
    order_no = models.CharField(max_length=20, unique=True, blank=True)
    member = models.ForeignKey(
        'member.Member',
        on_delete=models.PROTECT,  # 有訂單的客戶不准刪——歷史要留（呼應「停用不刪」）
        related_name='orders',
    )
    order_date = models.DateField(auto_now_add=True)
    # 總額永遠是「算出來的」（recalc_total），欄位只是快取查詢方便。
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    # 生命週期狀態（預設待付款）＋ 已收金額（收款時鎖成總額）。
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    note = models.CharField(max_length=200, blank=True)  # 備註（自由文字，選填）
    # ── 收貨資訊（讓訂單是一張像樣的銷貨單；聯絡人可與客戶不同，地址是這張單送去哪）──
    contact_name = models.CharField('聯絡人', max_length=50, blank=True)
    contact_phone = models.CharField('聯絡人電話', max_length=30, blank=True)
    shipping_address = models.CharField('收貨地址', max_length=200, blank=True)
    expected_ship_date = models.DateField('預計出貨日', null=True, blank=True)

    def __str__(self):
        return f'{self.order_no} {self.member} ${self.total} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        """建立後補上單號 order_no（需先存拿到 pk，再從 pk 衍生）。

        用 queryset.update() 直接寫欄位，避免遞迴呼叫 save()。
        單號穩定不變——之後任何 save（改總額/狀態）都不會重算它。
        """
        super().save(*args, **kwargs)
        if not self.order_no:
            self.order_no = f'OR-{self.pk:06d}'
            Order.objects.filter(pk=self.pk).update(order_no=self.order_no)

    def recalc_total(self):
        """鐵則：{訂單總額 = 所有明細小計加總}。明細有任何增刪改後呼叫。"""
        self.total = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        self.save(update_fields=['total', 'updated_at'])

    # ── 狀態機 ─────────────────────────────────────────
    @property
    def is_editable(self):
        """能不能改明細（鐵則：已出貨/終態鎖定）。"""
        return self.status in self.EDITABLE_STATUSES

    def available_actions(self):
        """目前狀態下「合法」的動作清單。給前端決定顯示哪些按鈕——
        但真相仍由 apply_transition() 再擋一次（前端只是體驗、後端才是牆）。"""
        return [action for action, t in self.TRANSITIONS.items() if self.status in t['from']]

    def apply_transition(self, action):
        """推進狀態機。非法轉移 → TransitionError（終態不可轉、跳步不可轉）。

        收款/作廢會連動帳款分錄（收款→記一筆收款、作廢→沖銷未收應收）——多表寫入，
        呼叫端請包 transaction.atomic（見 apis.py 的 _transition）。
        """
        from apps.billing.models import LedgerEntry   # 局部 import：避免 order↔billing 載入期耦合
        t = self.TRANSITIONS.get(action)
        if t is None:
            raise TransitionError(f'未知的動作：{action}')
        if self.status not in t['from']:
            allowed = '/'.join(self.Status(s).label for s in t['from'])
            raise TransitionError(
                f'「{self.get_status_display()}」不能{t["verb"]}（只有 {allowed} 可以）'
            )
        if action == 'pay':
            self.paid_amount = self.total   # [收款金額 = 總額]
            LedgerEntry.payment(self.member, self.total, order=self, memo=f'訂單 {self.order_no} 收款')
        elif action == 'cancel':
            # 作廢：沖掉這張訂單「還沒收」的應收，不留幽靈欠款（已收的退款＝金流，INTENT park）。
            # clamp ≥0：淨額為負代表客戶溢繳（貸方餘額），作廢不該把它吞掉，所以只沖非負部分。
            outstanding = max(LedgerEntry.order_net(self), Decimal('0'))
            LedgerEntry.reversal(self.member, outstanding, order=self,
                                 memo=f'訂單 {self.order_no} 作廢沖銷')
        self.status = t['to']
        self.save(update_fields=['status', 'paid_amount', 'updated_at'])

    # ── 帳款連動（event-sourced-ledger；每個動作只 append 分錄，見 apps/billing）──
    def post_initial_charge(self):
        """訂單建立完成（總額定案後）：開一筆應收。後台建單與成交生訂單都呼叫這個。"""
        from apps.billing.models import LedgerEntry
        LedgerEntry.charge(self.member, self.total, order=self, memo=f'訂單 {self.order_no} 應收')

    def post_adjustment(self, old_total):
        """改單後總額變動 → 補一筆調整（append-only 更正）：差額 >0 追加應收、<0 沖減。"""
        from apps.billing.models import LedgerEntry
        delta = self.total - old_total
        if delta > 0:
            LedgerEntry.charge(self.member, delta, order=self, memo=f'訂單 {self.order_no} 改單追加')
        elif delta < 0:
            LedgerEntry.reversal(self.member, -delta, order=self, memo=f'訂單 {self.order_no} 改單沖減')


class OrderItem(TimeStampedModel):
    """訂單裡的一個品項。訂單:明細 = 1:N。

    明細的 name / unit_price 是**建單當下的快照**（從 Product 抄一份，見 snapshot_from）——
    不是即時讀目錄。這樣目錄事後改價/改名/停售，這筆歷史明細都不動。
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # 指回目錄（報表/追溯用）。PROTECT：被明細引用的產品不准硬刪（呼應「停售不刪」）。
    product = models.ForeignKey('product.Product', on_delete=models.PROTECT, related_name='order_items')
    name = models.CharField(max_length=100)                          # 品名（建單當下快照）
    quantity = models.PositiveIntegerField()                         # 數量（>0 由 schema 驗）
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # 單價（建單當下快照）
    # 小計不接受手填——save() 算出來存（鐵則入 code 的樣子）。
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    @classmethod
    def snapshot_from(cls, order, product, quantity):
        """建單當下：把目錄的品名＋單價「抄一份」存進明細（快照）。

        這是「目錄 vs 明細」那一課的落點：訂單是歷史事實，目錄是當前真相。
        建立後改 product 的價格/名稱，這筆明細不受影響。
        """
        return cls.objects.create(
            order=order,
            product=product,
            name=product.name,            # 快照
            unit_price=product.unit_price,  # 快照
            quantity=quantity,
        )

    def save(self, *args, **kwargs):
        """鐵則：{明細小計 = 數量 × 單價}。不管誰存、怎麼存，這條永遠成立。

        Decimal(str(...))：不管上游塞進來的是 int / float / str / Decimal，
        先安全轉成 Decimal 再算——錢的運算永遠不讓 float 參與（會有二進位誤差）。
        """
        self.subtotal = Decimal(self.quantity) * Decimal(str(self.unit_price))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} x{self.quantity}'
