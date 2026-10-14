# Kế hoạch Dọn dẹp & Xử lý Mock API cho Operator

Tài liệu này lưu trữ chiến thuật và danh sách các tính năng cần dọn dẹp hoặc làm giả (Mock / Graceful Stubbing) ở phía Frontend để giao diện Operator không bị lỗi, không văng 404, và giữ nguyên được thiết kế UI chờ ngày Backend hoàn thiện.

## Chiến thuật "Graceful Stubbing"
Thay vì xóa file API hoặc để nguyên cho React Query gọi Axios sinh ra lỗi 404, chúng ta sẽ tạm thời ngắt kết nối Axios bên trong các hàm API của Frontend và trả về dữ liệu rỗng.

**Ví dụ:**
```typescript
export const getOutboundTasksApi = async () => {
  console.warn('[MOCK API] getOutboundTasksApi đang chờ Backend, tạm trả về rỗng');
  return []; 
};
```

---

## Danh sách công việc chi tiết

### Nhóm 1: Rác 100% (Tiến hành XÓA SẠCH)
Nhóm này Backend không tồn tại, và Frontend cũng đã có chức năng khác thay thế. Việc xóa giúp code nhẹ và đỡ rối.

- [ ] **Hệ thống Node (Entry/Exit/Start points)**
  - Xóa file: `frontend/src/api/node.ts`
  - Xóa file: `frontend/src/hooks/useNode.ts`
  - Xóa UI không dùng: `EntryPointSettingPage.tsx`, `ExitPointSettingPage.tsx`, `NodeManagementPanel.tsx`
- [ ] **Inventory Audit cũ** (Đã được thay thế bởi tính năng Stocktake)
  - Xóa file: `frontend/src/api/inventoryAudit.ts`
  - Xóa file: `frontend/src/hooks/useInventoryAudit.tsx`

### Nhóm 2: Lệch tên API (Tiến hành SỬA URL)
Backend đã làm nhưng Frontend đang gọi sai tên URL (định tuyến). Cần sửa lại chuỗi string URL trong Axios.

- [ ] **Tồn kho (Item Stock)**
  - Tình trạng: Frontend gọi `/api/v1/item-stock`, Backend là `/item-stocks`.
  - Hành động: Đổi thành `/api/v1/item-stocks` và đổi tham số `warehouse_id` thành `zone_id` cho đúng thiết kế.
- [ ] **Product vs Item**
  - Tình trạng: Nhánh Operator cũ dùng `/api/v1/product`, trong khi quy chuẩn hệ thống là `/api/v1/items`.
  - Hành động: Tạm thời trỏ URL của `api/product.ts` sang `/items` để có data thật. Về lâu dài sẽ gom `useProduct` vào `useItem`.

### Nhóm 3: Tính năng Operator "Ảo" (Tiến hành MOCK / STUB)
Khu vực này Backend chưa xây dựng Router. Sẽ áp dụng chiến thuật "Graceful Stubbing" cắt Axios.

- [ ] **Khu vực Outbound & Sorting (Chia chọn)**
  - `frontend/src/api/outboundTask.ts` (API: `/outbound-tasks/`)
  - `frontend/src/api/sortingWave.ts` (API: `/sorting-waves/`)
  - `frontend/src/api/sortingOrder.ts` (API: `/sorting-order-details/`)
  - Đảm bảo trả lại biến `zone_id` thay vì `warehouseId` bị sửa nhầm hôm trước.
- [ ] **Khu vực Inbound (Phân bổ)**
  - `frontend/src/api/inboundOperator.ts` (API: `/inbound-allocations/`) - Trừ hàm `accept-task` đã có backend, các hàm list khác cần bọc Mock.
- [ ] **Khu vực Robot**
  - `frontend/src/api/robotTask.ts` (API: `/robot-tasks/`)
- [ ] **Dọn dẹp Data Rác**
  - Xem xét gỡ bỏ các import trực tiếp từ `data/mockOperatorInbound.ts`, `data/mockOperatorOutbound.ts`, `data/mockNotifications.ts` nếu thay bằng Stub an toàn hơn.
