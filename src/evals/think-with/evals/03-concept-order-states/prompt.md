---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Skill, Read]
runs: 3
---
/think-with:lay-out 주문 상태 로직이 파일 네 개에 흩어져 있어서 헷갈려. 주문 상태가 어떻게 바뀌는지 보여줘.

`order/types.ts`

```ts
export type Status = "pending" | "paid" | "shipped" | "delivered" | "cancelled" | "refunded";
```

`order/payment.ts`

```ts
export function pay(o: Order) {
  if (o.status !== "pending") throw new Error("already processed");
  o.status = "paid";
}
```

`order/shipping.ts`

```ts
export function ship(o: Order) {
  if (o.status !== "paid") throw new Error("not paid");
  o.status = "shipped";
}

export function deliver(o: Order) {
  if (o.status !== "shipped") throw new Error("not shipped");
  o.status = "delivered";
  o.deliveredAt = new Date();
}
```

`order/cancel.ts`

```ts
export function cancel(o: Order) {
  if (o.status === "shipped" || o.status === "delivered") throw new Error("too late");
  if (o.status === "cancelled" || o.status === "refunded") return;
  // 결제된 주문을 취소하면 곧바로 환불 처리
  o.status = o.status === "paid" ? "refunded" : "cancelled";
}
```

`order/refund.ts`

```ts
export function refund(o: Order) {
  if (o.status !== "delivered") throw new Error("refund only after delivery");
  if (daysSince(o.deliveredAt) > 14) throw new Error("refund window closed");
  o.status = "refunded";
}
```
