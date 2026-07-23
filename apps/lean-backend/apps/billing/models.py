"""帳款（收費）的資料模型。規則來源：能力包/主幹/收費.md（內部管理系統的核心塊）。

這一塊講的是「客戶欠多少、收多少」——**應收帳款**。核心是一個 founding pattern：
**event-sourced-ledger（事件溯源帳）**——客戶的帳不是一個「餘額欄位」被人改來改去，
而是一條**只准往後加、永不修改**的分錄流（應收、收款、沖銷、調整）；餘額是**推導**出來的
（Σ 應收 − Σ 收款 − Σ 沖銷），不是存起來的真相。

為什麼要這樣（這就是這塊的教學命門）：
- 錢的帳最怕「有人把餘額改成他想要的數字」。分錄 append-only ＝ 每一分錢的來龍去脈都留痕、
  可稽核、可重算；餘額對不上時能一筆一筆攤開對。
- 改錯了不是回去改那筆，而是**新增一筆沖銷/調整**（就像會計的紅字沖銷）——歷史永遠不被竄改。

跟訂單怎麼串（一條故事：報價→成交→訂單→應收→收款）：
- 訂單**建立** → 開一筆**應收**（客戶欠這張訂單的錢）。
- 訂單**收款**（order 的 pay）→ 記一筆**收款**（欠款減少）。
- 訂單**作廢** → **沖銷**掉這張訂單還沒收的應收（不留幽靈欠款）。
- 訂單**改單**（總額變動）→ 補一筆**調整**（差額；append-only 的更正示範）。
分錄都掛在訂單上（order FK），所以能一路追回「這筆帳從哪張訂單來」。

承重牆（掛術軌，不 inline）：
- {分錄 append-only、不可改/刪} → assert-invariant（save/delete 守衛）。
- {客戶餘額 = Σ應收 − Σ收款 − Σ沖銷} → 推導（balance_for），不存可變真相。
"""
from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum

from apps._common.models import TimeStampedModel


class LedgerQuerySet(models.QuerySet):
    """append-only 砌在 QuerySet 層——連 bulk 路徑也擋。

    只擋單筆 instance.save()/delete() 不夠：`.update()`/`.delete()` 走 SQL、不經 Model.save()，
    一行 `LedgerEntry.objects.filter(...).update(amount=0)` 就能竄改帳。財務台帳的不可竄改保證
    必須連 bulk 面一起守，所以在這裡把 update/delete 兩條 bulk 入口也封死。
    """
    def update(self, *args, **kwargs):
        raise ValueError('帳款分錄不可修改（append-only）——要更正請新增一筆沖銷/調整')

    def delete(self, *args, **kwargs):
        raise ValueError('帳款分錄不可刪除（append-only）——要沖掉請新增一筆沖銷')


class LedgerEntry(TimeStampedModel):
    """帳款分錄：客戶帳上的一個事件。**append-only**——建了就不准改、不准刪。"""

    objects = LedgerQuerySet.as_manager()

    class Kind(models.TextChoices):
        # value（存 DB / 走 API）    , label（給人看的中文）
        CHARGE = 'CHARGE', '應收'      # 開一筆帳：客戶欠款 +amount（訂單建立時）
        PAYMENT = 'PAYMENT', '收款'    # 收到錢：客戶欠款 −amount（訂單收款時）
        REVERSAL = 'REVERSAL', '沖銷'  # 更正/取消：抵掉先前的應收 −amount（訂單作廢/改單沖減）

    # 每種分錄對「客戶應收餘額」的方向：應收 +，收款/沖銷 −。餘額 = Σ(方向×amount)。
    SIGN = {Kind.CHARGE: Decimal('1'), Kind.PAYMENT: Decimal('-1'), Kind.REVERSAL: Decimal('-1')}

    customer = models.ForeignKey(
        'member.Member',
        on_delete=models.PROTECT,        # 有帳的客戶不准刪——帳要留（呼應「停用不刪」）
        related_name='ledger_entries',
    )  # 客戶＝抽象槽（宿主 Member）
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # 一律正數（金額大小；方向看 kind）
    # 這筆帳關聯的訂單（追溯用）。PROTECT：有帳款分錄的訂單不准硬刪——刪了帳就斷了根，
    # 且刪除會 bulk 改寫分錄的 order_id（繞過 append-only）。財務單據要作廢、不是刪除。
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.PROTECT, null=True, blank=True,
        related_name='ledger_entries',
    )
    memo = models.CharField(max_length=200, blank=True)  # 這筆帳的說明（如「訂單 OR-000012 應收」）

    class Meta:
        verbose_name = '帳款分錄'
        ordering = ('id',)  # 依建立順序（分錄流是時間序，跑餘額靠這個序）

    def __str__(self):
        return f'[{self.get_kind_display()}] {self.customer} ${self.amount}'

    @property
    def signed_amount(self):
        """這筆分錄對「客戶應收餘額」的影響（帶正負號）。應收 +、收款/沖銷 −。"""
        return self.SIGN[self.kind] * self.amount

    # ── append-only 守衛（assert-invariant）─────────────────────
    def save(self, *args, **kwargs):
        """{分錄 append-only}：只准新增，不准修改。更正請新增一筆沖銷/調整。

        `_state.adding` 只有「第一次 insert」為 True；任何之後的 save() 都是更新 → 擋。
        """
        if not self._state.adding:
            raise ValueError('帳款分錄不可修改（append-only）——要更正請新增一筆沖銷/調整')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """{分錄不可刪}：帳的歷史永遠不被竄改。"""
        raise ValueError('帳款分錄不可刪除（append-only）——要沖掉請新增一筆沖銷')

    # ── 推導：餘額不是存的，是 Σ 出來的 ─────────────────────────
    @classmethod
    def _totals(cls, qs):
        """把一組分錄聚合成 (應收合計, 收款合計, 沖銷合計)。共用給客戶餘額與訂單淨額。"""
        agg = qs.aggregate(
            charged=Sum('amount', filter=Q(kind=cls.Kind.CHARGE)),
            paid=Sum('amount', filter=Q(kind=cls.Kind.PAYMENT)),
            reversed_=Sum('amount', filter=Q(kind=cls.Kind.REVERSAL)),
        )
        z = Decimal('0')
        return (agg['charged'] or z, agg['paid'] or z, agg['reversed_'] or z)

    @classmethod
    def balance_for(cls, customer):
        """{客戶應收餘額 = Σ應收 − Σ收款 − Σ沖銷}。推導值，不存可變真相。"""
        charged, paid, rev = cls._totals(cls.objects.filter(customer=customer))
        return charged - paid - rev

    @classmethod
    def order_net(cls, order):
        """一張訂單目前在帳上的「未收淨額」（應收 − 收款 − 沖銷）。作廢時用它算要沖多少。"""
        charged, paid, rev = cls._totals(cls.objects.filter(order=order))
        return charged - paid - rev

    # ── 開帳原語（都只是 append 一筆；訂單生命週期呼叫這些）───────
    @classmethod
    def _post(cls, kind, customer, amount, order=None, memo=''):
        """唯一的寫入口：append 一筆分錄。金額 0 不記（省得留空事件）；負數＝呼叫端算錯，擋。"""
        if amount < 0:
            raise ValueError(f'分錄金額不可為負（{kind} {amount}）——方向由 kind 決定，amount 一律正數')
        if amount == 0:
            return None
        return cls.objects.create(kind=kind, customer=customer, amount=amount, order=order, memo=memo)

    @classmethod
    def charge(cls, customer, amount, order=None, memo=''):
        """開一筆應收（客戶欠款增加）。"""
        return cls._post(cls.Kind.CHARGE, customer, amount, order, memo)

    @classmethod
    def payment(cls, customer, amount, order=None, memo=''):
        """記一筆收款（客戶欠款減少）。"""
        return cls._post(cls.Kind.PAYMENT, customer, amount, order, memo)

    @classmethod
    def reversal(cls, customer, amount, order=None, memo=''):
        """沖銷一筆先前的應收（作廢/改單沖減）。"""
        return cls._post(cls.Kind.REVERSAL, customer, amount, order, memo)
