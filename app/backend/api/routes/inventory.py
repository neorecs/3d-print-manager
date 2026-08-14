from fastapi import APIRouter
from api.routes_shared import *

router = APIRouter()

@router.get("/inventory/products")
def list_product_inventory(db: Session = Depends(get_db)):
    return list_product_inventory_rows(db)


@router.post("/inventory/products")
def create_product_inventory(payload: ProductInventoryCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.scalar(select(ProductInventory).where(ProductInventory.product_variant_id == payload.product_variant_id))
    if existing:
        raise HTTPException(status_code=409, detail="Voor deze productvariant bestaat al een voorraadregel")
    return create_inventory_record(db, payload.model_dump(), request.state.user_email)


@router.put("/inventory/products/{item_id}")
def update_product_inventory(item_id: int, payload: ProductInventoryCreate, request: Request, db: Session = Depends(get_db)):
    return replace_inventory_record(db, item_id, payload.model_dump(), request.state.user_email)


@router.get("/inventory/movements")
def list_inventory_movements(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(InventoryMovement).order_by(InventoryMovement.id.desc())).all())


@router.post("/inventory/products/{item_id}/adjust")
def adjust_product_inventory(item_id: int, quantity: int, request: Request, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return adjust_inventory_stock(db, item, quantity, request.state.user_email)


@router.post("/inventory/products/{item_id}/reserve")
def reserve_product_inventory(item_id: int, quantity: int, request: Request, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return reserve_inventory_stock(db, item, quantity, request.state.user_email)


@router.post("/inventory/products/{item_id}/release")
def release_product_inventory(item_id: int, quantity: int, request: Request, db: Session = Depends(get_db)):
    item = get_or_404(db, ProductInventory, item_id)
    return release_inventory_stock(db, item, quantity, request.state.user_email)


@router.get("/filament")
def list_filament(db: Session = Depends(get_db)):
    return list_rows(db.scalars(select(FilamentSpool).order_by(FilamentSpool.id)).all())


@router.post("/filament")
def create_filament(payload: FilamentSpoolCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["price_per_gram"] = data["purchase_price"] / data["initial_weight_grams"]
    item = FilamentSpool(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return to_dict(item)


@router.put("/filament/{item_id}")
def update_filament(item_id: int, payload: FilamentSpoolCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, FilamentSpool, item_id)
    data = payload.model_dump()
    data["price_per_gram"] = data["purchase_price"] / data["initial_weight_grams"]
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    return to_dict(item)


@router.post("/filament/{item_id}/adjust")
def adjust_filament(item_id: int, remaining_weight_grams: float, db: Session = Depends(get_db)):
    if remaining_weight_grams < 0:
        raise HTTPException(status_code=400, detail="Resterend gewicht mag niet negatief zijn")
    item = get_or_404(db, FilamentSpool, item_id)
    if remaining_weight_grams > item.initial_weight_grams:
        raise HTTPException(status_code=400, detail="Resterend gewicht kan niet hoger zijn dan het startgewicht")
    item.remaining_weight_grams = remaining_weight_grams
    db.commit()
    return to_dict(item)


