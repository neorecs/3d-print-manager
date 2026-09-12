export function ordersListHref(status = "alle", page = 1) {
  const params = new URLSearchParams();
  if (status && status !== "alle") params.set("status", status);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/orders?${query}` : "/orders";
}

export function orderDetailHref(orderId: number, returnTo = "/orders") {
  return `/orders/${orderId}?returnTo=${encodeURIComponent(safeOrdersReturnHref(returnTo))}`;
}

export function safeOrdersReturnHref(value?: string) {
  if (!value) return "/orders";
  try {
    const url = new URL(value, "http://internal");
    if (url.origin !== "http://internal" || url.pathname !== "/orders") return "/orders";
    return `${url.pathname}${url.search}`;
  } catch {
    return "/orders";
  }
}

export function printJobHref(printJobId: number) {
  return `/printplanning?job=${printJobId}#printtaak-${printJobId}`;
}

export function productInventoryHref(productId: number) {
  return `/catalogus/${productId}?tab=voorraad`;
}
