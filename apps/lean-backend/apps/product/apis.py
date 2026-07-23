"""產品管理 API。規則來源：intents/商品管理.md。

- 列表（搜尋 + 分頁；active_only 只看在售）→ GET  /product
- 建立                                    → POST /product
- 改（品名/單價）                          → PUT  /product/{id}
- 停售                                    → POST /product/{id}/deactivate
- 重新開售                                → POST /product/{id}/reactivate

鐵則把關：
- {一 sku 一產品} → sku unique（DB），撞了轉 422。
- {停售=停售不刪} → 只有 deactivate 改 is_active，**沒有 DELETE 端點**。
"""
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.product.models import Product
from apps.product.schemas import (
    ProductIn,
    ProductListSchema,
    ProductSchema,
    ProductUpdateIn,
)

router = Router(tags=['product'])


@router.get('', response=ProductListSchema)
def list_products(request, page: int = 1, page_size: int = 10, search: str = '', active_only: bool = False):
    """search 模糊搜品名，active_only=True 只看在售（開單表單的產品 select 用這個）。"""
    qs = Product.objects.order_by('sku')
    if search:
        qs = qs.filter(name__icontains=search)
    if active_only:
        qs = qs.filter(is_active=True)
    count = qs.count()
    start = (max(page, 1) - 1) * page_size
    return {'items': list(qs[start:start + page_size]), 'count': count}


@router.post('', response=ProductSchema)
def create_product(request, payload: ProductIn):
    try:
        return Product.objects.create(**payload.dict())
    except IntegrityError:
        raise HttpError(422, f'品號「{payload.sku}」已存在（一 sku 一產品）')


@router.put('/{product_id}', response=ProductSchema)
def update_product(request, product_id: int, payload: ProductUpdateIn):
    """改品名/單價。注意：改單價只影響「之後的新訂單」，已成立訂單的明細是快照、不受影響。"""
    product = get_object_or_404(Product, pk=product_id)
    product.name = payload.name
    product.unit_price = payload.unit_price
    product.save(update_fields=['name', 'unit_price', 'updated_at'])
    return product


@router.post('/{product_id}/deactivate', response=ProductSchema)
def deactivate_product(request, product_id: int):
    """停售：資料保留（不 DELETE）；歷史訂單明細仍指得到。"""
    product = get_object_or_404(Product, pk=product_id)
    product.is_active = False
    product.save(update_fields=['is_active', 'updated_at'])
    return product


@router.post('/{product_id}/reactivate', response=ProductSchema)
def reactivate_product(request, product_id: int):
    """重新開售。"""
    product = get_object_or_404(Product, pk=product_id)
    product.is_active = True
    product.save(update_fields=['is_active', 'updated_at'])
    return product
