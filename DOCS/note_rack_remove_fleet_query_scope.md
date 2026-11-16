# Note: Phạm vi xóa Rack + `containerQuery` (Pha 1 = chỉ A)

Ngày ghi: 2026-11-16

## Đã implement (Pha 1 — A)

**Luồng:** Admin xóa tay trên `RackManagementPage` → `DELETE /api/v1/production/racks/{id}` → `remove_rack_container`.

1. Luôn gọi `POST /amr/containerQuery` theo đúng `containerCode` (`emptyFullStatus=2`, `containerModelCode` từ config).
2. Query lỗi / timeout → **giữ nguyên WMS**.
3. `success` + `data: []` (không có `containerCode` khớp) → **cho phép thu hồi WMS**, không gọi `containerOut`.
4. Có trên Fleet + `isCarry=1` → **chặn xóa**.
5. Có trên Fleet + không mang → `containerOut` rồi mới thu hồi WMS.
6. `containerOut` lỗi thật → **giữ nguyên WMS**.
7. Chỉ match theo `containerCode` (không bắt buộc khớp `nodeCode`).
8. Không phụ thuộc cờ `fleet_registered` khi quyết định có query hay không.

## Chưa làm — tình huống B (webhook hạ xe rỗng)

**Chỗ code:** `webhook_handler` khi mission trả về `EMPTY_CART_BUFFER` / `RETURN_EMPTY_CART` → gọi `fleet_container_out` trực tiếp.

**Triệu chứng có thể gặp sau này:**

- AMR đã hạ xe thành công nhưng Fleet thực tế không còn container → `containerOut` fail → rack bị `status=out_failed`, `is_active=true`.
- Admin phải vào trang Quản lý Rack bấm **Xóa Rack** (luồng A đã có query) để gỡ kẹt.

**Khi nào cân nhắc mở rộng B:** nếu hay xuất hiện `out_failed` vì “Fleet không có xe”, có thể trước `containerOut` ở webhook cũng `containerQuery`; `data:[]` thì bỏ qua Out và thu hồi WMS luôn (giống A).

**Rủi ro cần hỏi lại trước khi làm B:** webhook chạy tự động — nếu query timeout mà vẫn thu hồi WMS sẽ lệch Fleet; nên giữ nguyên rule “query fail = không đụng WMS”.

## Chưa làm — tình huống C (Đổi vị trí / relocate)

**Chỗ code:** `update_rack_location` → `containerOut` vị trí cũ → `containerIn` vị trí mới.

**Triệu chứng có thể gặp sau này:**

- WMS còn rack, Fleet không còn ở vị trí cũ → bước Out fail → không đổi được vị trí dù thực tế Fleet đã trống.
- Hoặc `fleet_registered=false` nhưng Fleet vẫn còn container ở chỗ khác → In/Out lệch.

**Khi nào cân nhắc mở rộng C:** Admin báo không đổi vị trí được vì Out “container không tồn tại”. Khi đó có thể query theo `containerCode` trước Out:

- Không có trên Fleet → bỏ qua Out, chỉ In vị trí mới.
- Có trên Fleet → Out (position có thể lấy từ Fleet `nodeCode` nếu cần) rồi In.

**Rủi ro cần hỏi lại trước khi làm C:** relocate là đồng bộ 2 chiều; bỏ Out khi query rỗng có thể OK, nhưng nếu query sai / filter `emptyFullStatus` làm miss container thì dễ để lại ghost trên Fleet.
