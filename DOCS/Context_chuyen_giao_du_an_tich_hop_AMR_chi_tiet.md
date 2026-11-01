CONTEXT CHUYỂN GIAO DỰ ÁN
TÍCH HỢP AMR VÀO DÂY CHUYỀN SẢN XUẤT

Bản bàn giao chi tiết cho người mới tiếp quản / AI khác

Phiên bản 1.3 | Cập nhật ngày 15/10/2026 (Đặc tả chi tiết UI PDA 4.2 inch, Wizard 3 bước Nguyên liệu & Popup xác nhận)

Mục đích: cung cấp bối cảnh nghiệp vụ và các quyết định hiện có để người mới có thể tiếp tục công việc mà không phải hỏi lại từ đầu. Đây không phải đặc tả kỹ thuật cuối cùng, cũng không phải tài liệu API đã xác minh.


## 0. Cách đọc tài liệu và nguyên tắc quan trọng


ĐÃ XÁC NHẬN: người dùng đã nói rõ hoặc đã thống nhất.

ĐỊNH HƯỚNG: ý tưởng đang được ưu tiên nhưng chưa được nhà máy/nhà cung cấp xác nhận.

CẦN XÁC MINH: thông tin còn thiếu; tuyệt đối không tự coi là sự thật.

ĐỀ XUẤT: gợi ý thiết kế để giảm lỗi, cần được xem xét trước khi triển khai.

Nguyên tắc cho người tiếp quản: không hỏi lại những điều đã rõ; không dồn quá nhiều câu hỏi kỹ thuật một lúc; đi theo thứ tự nghiệp vụ → vai trò AMR/Fleet Manager → API/trạng thái → dữ liệu → lỗi/ngoại lệ → code.

Không bịa endpoint, HTTP method, payload, mã trạng thái, cách định danh xe hoặc cơ chế gắp/thả. Những thông tin này phải lấy từ tài liệu API hoặc xác minh với nhà cung cấp.


## 1. Tóm tắt dự án


Người dùng phụ trách phân tích nghiệp vụ và phối hợp tích hợp AMR vào dây chuyền nhà máy. Đây không phải hệ thống WMS truyền thống. Trọng tâm là điều phối các xe/cart mang sản phẩm hoặc nguyên liệu giữa khu nguyên liệu, các CNC/trạm sản xuất và khu tẩy rửa, theo model sản phẩm và route công đoạn đã cấu hình.

Ứng dụng nghiệp vụ dự kiến có giao diện tablet tại CNC để công nhân gọi xe và xác nhận hoàn thành công đoạn. Ứng dụng quản lý route, tiến độ sản xuất, điều kiện hợp lệ của xe và yêu cầu vận chuyển. Fleet Manager (FM) quản lý đội robot, nhận yêu cầu vận chuyển, điều phối AMR và cung cấp trạng thái robot/task.

Ba luồng chính:

Cấp nguyên liệu: công nhân tại điểm sản xuất yêu cầu model từ vị trí tương ứng trong khu nguyên liệu; AMR mang xe tới điểm bắt đầu sản xuất.

Chuyển giữa công đoạn: công nhân tại CNC đích (CNC-X) cần xe, chọn model; hệ thống tự động quét toàn bộ map tìm cart model đó thỏa mãn (đã hoàn thành bước trước, CNC-X là bước hợp lệ tiếp theo theo route, chưa bị giữ) và tự động chọn xe gần nhất trên map để điều phối AMR lấy và giao tại CNC-X.

Sau công đoạn cuối: công nhân xác nhận hoàn thành; ứng dụng kiểm tra slot tẩy rửa còn trống và yêu cầu AMR đưa xe tới đó.

Nguyên tắc quan trọng nhất: hoàn thành công đoạn sản xuất và hoàn thành nhiệm vụ vận chuyển là hai sự kiện khác nhau. Công nhân xác nhận tiến độ sản xuất; FM báo trạng thái task AMR.


## 2. Mục tiêu, phạm vi và giới hạn



## 2.1 Mục tiêu


Giảm thao tác điều phối thủ công và làm rõ cách công nhân gọi xe.

Chỉ chuyển xe đúng model, đúng vị trí và đủ điều kiện theo route.

Liên kết tiến độ sản xuất với vận chuyển mà không đánh đồng hai trạng thái.

Theo dõi task AMR thông qua Fleet Manager.

Chốt nghiệp vụ trước khi thiết kế database, API backend, UI và code.


## 2.2 Trong phạm vi


Cấu hình route sản xuất theo model.

Theo dõi tiến độ công đoạn của từng xe/cart.

Công nhân tạo yêu cầu vận chuyển từ tablet.

Cấp xe từ khu nguyên liệu.

Chuyển xe sau công đoạn cuối sang khu tẩy rửa.

Gửi yêu cầu task tới FM, nhận xác nhận và theo dõi trạng thái.


## 2.3 Không được tự mặc định


Không coi đây là WMS đầy đủ có nhập/xuất kho, lô hàng hay tồn kho tổng quát.

Không tự động gọi AMR ngay khi công đoạn trước hoàn thành.

Không giả định FM có API hủy, retry, ưu tiên, chỉ định robot cụ thể hoặc xếp hàng task.

Không giả định AMR tự lấy/thả cart; cơ chế vật lý chưa rõ.

Nếu không có xe đủ điều kiện, định hướng hiện tại là báo cho công nhân, không tự tạo hàng đợi ngầm.


## 3. Thuật ngữ và thành phần



## 4. Khu vực và route



## 4.1 Các khu vực


Khu nguyên liệu: có các vị trí lấy xe theo model; ví dụ 7 model tương ứng 7 slot.

Khu sản xuất: gồm các CNC/trạm trong route của từng model.

Khu tẩy rửa: có nhiều slot để nhận xe sau công đoạn cuối.

Có một điểm đầu dây chuyền/điểm nhận nguyên liệu; vị trí đích chính xác vẫn cần xác nhận.


## 4.2 Route theo model


Quản trị viên cấu hình route theo từng model; phần mềm không được hard-code một route chung.

Ví dụ đã thảo luận: Model A đi CNC-01 → CNC-03 HOẶC CNC-04 → CNC-05 → khu tẩy rửa.

CNC-03 và CNC-04 là hai máy thay thế cho cùng một bước.

Một cart chỉ cần qua một trong hai máy, không phải qua cả hai.

Nếu công nhân tại CNC-03 gọi xe, đích là CNC-03. Nếu công nhân tại CNC-04 gọi, đích là CNC-04.

Không tự động chọn đích thay thế trong luồng hiện tại khi đã có một CNC cụ thể gọi.

Route chỉ được sửa khi thỏa điều kiện 'không có xe đang chạy'; ý nghĩa chính xác của cụm này chưa chốt.


## 4.3 Route là điều kiện nghiệp vụ


Không chuyển xe tới bất kỳ CNC nào chỉ vì có yêu cầu. Phải kiểm tra model, bước trước đã hoàn thành, vị trí nguồn, bước kế tiếp hợp lệ và xe chưa bị task khác chiếm dụng.

Ví dụ, nếu route yêu cầu CNC-01 trước CNC-03/04, xe chưa được xác nhận hoàn thành CNC-01 thì không đủ điều kiện chuyển sang CNC-03/04.


## 5. Luồng A — cấp nguyên liệu



## 5.1 Luồng chính


Công nhân tại điểm sản xuất mở tablet và tạo yêu cầu cấp nguyên liệu.

Công nhân chọn model và vị trí nguồn trong khu nguyên liệu, trừ khi sau này thống nhất tự ánh xạ model → nguồn.

Ứng dụng kiểm tra model, nguồn và điều kiện yêu cầu.

Ứng dụng kiểm tra xe/cart phù hợp có ở nguồn và chưa bị task khác giữ hay không.

Ứng dụng gửi task có ý nghĩa nghiệp vụ: pickup ở vị trí nguyên liệu, drop-off tại điểm bắt đầu sản xuất.

FM accept/reject task; ứng dụng lưu phản hồi và liên kết task với yêu cầu nghiệp vụ.

Nếu accept, ứng dụng theo dõi trạng thái.

Khi FM báo completed, ứng dụng cập nhật trạng thái vận chuyển. Việc bắt đầu sản xuất là bước nghiệp vụ riêng.


## 5.2 Đã biết


Yêu cầu xuất phát từ công nhân sản xuất, không phải thao tác của nhân viên kho trong mô hình hiện tại.

Không có cơ sở để mặc định ERP tự kích hoạt lệnh.

Có các slot nguyên liệu riêng theo model.


## 5.3 Cần xác minh


Điểm đích là đầu dây chuyền chung hay phụ thuộc CNC/model?

Ai/cái gì đánh dấu xe đã được lấy khỏi slot nguồn?

Nếu nguồn không có xe, thông báo thế nào và công nhân có gọi lại được không?

Nếu FM nhận task nhưng phản hồi bị mất, cách đối soát để tránh task trùng?

Sau khi giao xe, trạng thái FM có đủ để đánh dấu xe sẵn sàng sản xuất hay cần công nhân xác nhận?


## 6. Luồng B — chuyển giữa các công đoạn



## 6.1 Luồng chính


Công nhân tại CNC đích mở tablet.

Chọn model cần xử lý.

Hệ thống tự động quét toàn bộ map/layout xưởng để tìm các cart Model A thỏa mãn: (1) Cart đã bấm hoàn thành ở công đoạn trước; (2) CNC-X là bước hợp lệ tiếp theo trong route của Model A; (3) Cart chưa bị task khác chiếm dụng.

Hệ thống tự động chọn cart gần nhất theo khoảng cách trên map tới CNC-X (không bắt công nhân chọn nguồn). CNC-X được coi là sẵn sàng nhận xe; đích giao là CNC-X.

Nếu tìm thấy cart hợp lệ gần nhất, ứng dụng tạo yêu cầu vận chuyển.

Nếu có xe hợp lệ, ứng dụng tạo yêu cầu vận chuyển.

Gửi task tới FM với pickup tại vị trí cart được chọn và drop-off tại CNC-X.

FM trả accept/reject; nếu accept, ứng dụng theo dõi trạng thái task.

Khi FM báo completed sau khi thả xe, ứng dụng cập nhật vận chuyển hoàn tất và vị trí cart.


## 6.2 Quyết định/định hướng


Công nhân chủ động gọi khi cần; không tự điều xe ngay khi công đoạn trước vừa hoàn thành.

Không tự queue khi không có cart hợp lệ; hiện ưu tiên báo 'không có xe/cart sẵn sàng'.

ĐÃ XÁC NHẬN: Tự động chọn xe gần nhất trên map. Công nhân tại CNC-X chỉ cần chọn Model, hệ thống tự quét toàn bộ map tìm cart hợp lệ đã hoàn thành công đoạn trước và chọn xe gần nhất để điều phối AMR.

ĐÃ XÁC NHẬN VỀ UI: Giao diện tablet tối giản, công nhân chỉ chọn Model, không cần chọn CNC nguồn thủ công.


## 6.3 Ví dụ


Model A: CNC-01 → CNC-03 hoặc CNC-04 → CNC-05 → tẩy rửa. Công nhân tại CNC-03 chọn Model A. Hệ thống quét thấy cart Model A tại CNC-01 đã hoàn thành CNC-01 và CNC-03 là bước kế tiếp hợp lệ, nên tự động chọn cart này (xe gần nhất) và điều AMR.

Hợp lệ: cart Model A ở CNC-01, đã hoàn thành công đoạn CNC-01, chưa bị task khác giữ và route cho phép CNC-03.

Không hợp lệ: cart chưa hoàn thành CNC-01; cart ở vị trí không thuộc route; cart đang bị task khác lấy; hoặc route không cho quay lại CNC-03.

Không có xe hợp lệ: báo rõ lý do; không tạo task ngầm hay queue tự động.


## 6.4 Cần xác minh


ĐÃ CHỐT: Nếu có nhiều cart hợp lệ, hệ thống tự động chọn cart gần nhất theo khoảng cách trên bản đồ tới trạm gọi.

Có cho phép hủy yêu cầu sau khi FM accept không? Chưa rõ API có hỗ trợ.

Nếu vị trí/thông tin nguồn thay đổi sau lúc mở form, phải kiểm tra lại trước khi gửi task.

Nếu task accept rồi robot lỗi, trạng thái nghiệp vụ và quy trình khôi phục ra sao?


## 7. Luồng C — sau công đoạn cuối tới khu tẩy rửa



## 7.1 Luồng chính


Công nhân ở công đoạn cuối xác nhận hoàn thành trên tablet.

Ứng dụng cập nhật tiến độ sản xuất: cart hoàn thành công đoạn cuối.

Ứng dụng kiểm tra slot tẩy rửa còn trống.

Nếu có slot, tạo yêu cầu pickup tại CNC cuối, drop-off tại slot tẩy rửa được chọn.

Gửi task tới FM, nhận accept/reject và theo dõi trạng thái.

Khi FM báo completed sau khi thả xe, cập nhật vị trí cart và trạng thái vận chuyển.

Khi nhân viên lấy cart ra khỏi khu tẩy rửa để rửa/xử lý, nhân viên cập nhật vị trí thủ công.


## 7.2 Đã rõ và chưa rõ


ĐÃ RÕ: nhân viên cập nhật vị trí khi lấy cart khỏi khu tẩy rửa.

CẦN XÁC MINH: slot được đánh dấu bận lúc task accept, AMR tới, hay FM báo đã thả xe?

CẦN XÁC MINH: nếu mọi slot đầy, giữ cart ở CNC cuối, báo lỗi hay có buffer?

CẦN XÁC MINH: ai xác nhận cart đã đúng slot nếu không có cảm biến/feedback vị trí chi tiết?

CẦN XÁC MINH: sau khi cart rời khu tẩy rửa, trạng thái nghiệp vụ tiếp theo là gì?


## 8. Phân chia trách nhiệm ứng dụng và FM



## 9. Ba vòng đời trạng thái — phải tách riêng



## 9.1 Yêu cầu nghiệp vụ


Đây là yêu cầu do công nhân tạo. Có thể cần các trạng thái khái niệm: được tạo → đang kiểm tra → không đủ điều kiện / đã gửi FM → FM accept/reject → đang thực hiện → hoàn tất / thất bại / cần đối soát. Đây chỉ là mô hình gợi ý, không phải enum API chính thức.


## 9.2 Tiến độ sản xuất của cart


Theo dõi công đoạn gần nhất hoàn thành, công đoạn kế tiếp hợp lệ, trạng thái công đoạn, vị trí vật lý được biết và cart có bị yêu cầu/task giữ chỗ hay không. Những trường cụ thể cần chốt sau.


## 9.3 Trạng thái task/robot


FM là nguồn trạng thái vận chuyển/robot theo thông tin hiện có. Không tự suy ra enum như queued, dispatched, moving, arrived, loading/unloading nếu chưa có tài liệu.


## 9.4 Những cặp không được nhầm


Công nhân xác nhận công đoạn hoàn thành ≠ AMR vận chuyển xong.

Ứng dụng gửi request thành công ≠ FM accept.

FM accept ≠ robot đã di chuyển.

Robot tới điểm đích ≠ cart đã được thả xuống, trừ khi API định nghĩa rõ.

FM completed ≠ công nhân đã bắt đầu công đoạn tiếp theo.

Nhân viên cập nhật cart rời slot tẩy rửa ≠ task trước bị hủy.


## 10. Nguyên tắc thiết kế để tránh lỗi


Không tạo task nếu cart sai model, sai route hoặc chưa hoàn thành bước trước.

Không cho hai task đồng thời lấy cùng cart hoặc cùng chiếm một slot đích.

Kiểm tra lại cart/nguồn/đích ngay trước khi gửi task vì trạng thái có thể đổi.

Lưu liên kết giữa ID yêu cầu nội bộ và task ID từ FM nếu có.

Không đánh dấu vận chuyển hoàn tất chỉ dựa trên accept.

Nếu timeout sau khi gửi request, đừng gửi lại task y hệt ngay khi chưa biết FM đã nhận chưa; có thể tạo task trùng. Cần truy vấn/đối soát.

Ghi log thời điểm tạo, request gửi, phản hồi, cập nhật trạng thái và lỗi.

Không queue ngầm nếu không có cart đủ điều kiện theo định hướng hiện tại.

Không tự định nghĩa 'không có xe đang chạy' khi sửa route.

Nếu vị trí cart chưa chắc chắn, đừng hiển thị như vị trí đã xác minh.

Không xây UI cho hủy/retry/ưu tiên/chọn robot trước khi xác minh API.


## 11. Tích hợp AMR — cần xác minh với nhà cung cấp



## 11.1 Ba câu hỏi ưu tiên


AMR lấy và thả cart như thế nào? Tự động hoàn toàn hay cần công nhân hỗ trợ? Điều này quyết định thao tác tại điểm lấy/thả và cách xác nhận hoàn tất.

API tạo task cần trường gì? Chỉ điểm lấy/điểm thả hay còn robot ID, cart ID, task type hoặc tham số khác? Xin schema chính thức.

FM có tự xếp hàng/điều phối nhiều task hay ứng dụng phải chờ task trước xong mới gửi task tiếp? Hỏi rõ giới hạn task đồng thời và quy tắc từ chối.


## 11.2 Checklist kỹ thuật tiếp theo


Cách xác thực, môi trường, phiên bản API và Swagger/OpenAPI nếu có.

Endpoint/method/payload tạo task; trường bắt buộc và giá trị hợp lệ.

Schema accept/reject; task ID và tính duy nhất.

Cách lấy trạng thái: polling, callback/webhook, websocket hay cách khác.

Enum trạng thái task và ý nghĩa chính xác.

API vị trí robot; có API vị trí cart hay chỉ vị trí robot.

Mã lỗi khi robot bận, điểm không hợp lệ, task bị từ chối.

Có tra cứu task theo request ID khi timeout/mất kết nối không.

Có API hủy task không; điều kiện và ngữ nghĩa hủy.

Có tín hiệu xác nhận pickup/drop-off thực tế không.

Mapping mã điểm nội bộ với mã node/location của FM.

Giới hạn tốc độ gọi, số task đồng thời và hỗ trợ idempotency/request ID.

Cách làm: xin tài liệu API hoặc một request/response thật chạy thành công, sau đó lập bảng mapping nghiệp vụ → trường API. Không phỏng đoán payload.


## 12. Câu hỏi nghiệp vụ còn mở



## 13. Những điều làm rõ gần nhất


Khi công nhân tại một CNC cụ thể gọi xe, đích giao là CNC đang gọi. Người dùng nói CNC đó được coi là sẵn sàng nhận xe trong ngữ cảnh này; không cần hỏi lại cách chọn giữa hai CNC thay thế cho luồng này.

Khi cart được lấy khỏi khu tẩy rửa để đưa đi rửa, nhân viên cập nhật vị trí thủ công.

Người dùng muốn dừng brainstorm tạm thời và có một file context chi tiết để đưa cho người mới/AI khác.
- ĐÃ XÁC NHẬN (15/10/2026): Luồng B tự động quét map và chọn cart gần nhất thỏa mãn: (1) cart đã bấm hoàn thành ở CNC trước, (2) CNC gọi là bước hợp lệ tiếp theo của model. Không yêu cầu công nhân chọn trạm nguồn.
- ĐÃ XÁC NHẬN (15/10/2026): Kế hoạch dọn dẹp codebase Kuka WMS: Xóa toàn bộ module Masan FMCG và giao diện Operator kho cũ; tạm thời giữ lại các trang Admin.
- ĐÃ XÁC NHẬN (15/10/2026 - Kết quả Grill 5 câu hỏi nghiệp vụ then chốt):
  1. Khoảng cách xe gần nhất: Tính theo công thức khoảng cách 2D Euclidean sqrt((x2-x1)^2 + (y2-y1)^2) dựa trên tọa độ (map_x, map_y) của trạm trên sơ đồ xưởng.
  2. Tranh chấp xe & Hàng đợi (Queue): Khi 2 máy song song cùng gọi xe, máy bấm trước được gán xe. Máy bấm sau nhận thông báo không có xe và ĐƯỢC ĐƯA VÀO HÀNG ĐỢI (Queue) để hệ thống tự động quét liên tục; ngay khi có xe hoàn thành ở công đoạn trước thì tự động điều phối tới máy đang chờ.
  3. Khu tẩy rửa đầy: Giữ xe tại bàn máy CNC cuối và ĐƯA VÀO HÀNG ĐỢI TẨY RỬA. Khi có slot tẩy rửa trống (nhân viên lấy xe đi rửa), hệ thống tự động phát lệnh AMR tới lấy xe ở CNC cuối đưa vào slot trống.
  4. Cấp nguyên liệu (Luồng A): AMR chở xe trực tiếp từ slot nguyên liệu tới máy CNC đầu tiên trong route của model đó (Phương án A).
  5. Thao tác thả xe: Robot AMR tự động hạ/nhả xe xuống trạm vật lý và Fleet Manager gửi tín hiệu completed (không bắt công nhân bấm nút xác nhận nhận xe trên tablet).

Câu hỏi AMR tự lấy/thả hay cần công nhân hỗ trợ đã được đặt ra nhưng chưa có câu trả lời. Không coi là đã xác nhận.


## 14. Demo HTML hiện có và giới hạn


Có file amr_integration_demo.html để minh họa thao tác tablet/CNC, chọn model/nguồn, tiến độ và mô phỏng yêu cầu vận chuyển.

Demo chỉ mô phỏng UI/nghiệp vụ, chưa tích hợp FM thật.

Trạng thái robot/task trong demo là dữ liệu minh họa, không chứng minh API hoặc hành vi vật lý.

Không dùng demo làm căn cứ cho tên endpoint, payload, enum trạng thái hoặc khả năng AMR.

Dùng demo để kiểm tra người dùng hiểu luồng thao tác; vẫn phải xác nhận quy trình với nhà máy và API với nhà cung cấp.


## 15. Gợi ý dữ liệu nghiệp vụ tối thiểu — chưa phải schema cuối


Không nên gộp mọi thứ vào một trường trạng thái duy nhất của cart. Vị trí vật lý, tiến độ sản xuất và trạng thái vận chuyển là ba chiều riêng, có thể thay đổi theo các thời điểm khác nhau.


## 16. Ví dụ xuyên suốt



## 16.1 CNC-01 → CNC-03


Công nhân hoàn thành công đoạn tại CNC-01 và xác nhận trên tablet.

Ứng dụng ghi nhận bước sản xuất hoàn tất; chưa tự động gửi AMR.

Khi CNC-03 cần xe, công nhân chỉ cần chọn Model A trên tablet. Hệ thống quét toàn bộ map, tìm cart Model A tại CNC-01 (đã hoàn thành bước trước, chưa bị task giữ, CNC-03 là bước tiếp theo hợp lệ), chọn xe gần nhất và tạo task gửi FM.

Ứng dụng tìm cart Model A tại CNC-01, đã hoàn thành bước trước, chưa bị task khác giữ và route cho phép CNC-03.

Nếu không có xe phù hợp, hiển thị thông báo; không tự queue.

Nếu có xe, gửi task cho FM.

FM accept: lưu task ID nếu có và theo dõi; chưa đánh dấu giao xong.

FM completed sau khi thả xe: cập nhật vận chuyển hoàn tất và vị trí CNC-03.

Công nhân làm công đoạn ở CNC-03 rồi xác nhận hoàn thành; đây là sự kiện sản xuất mới.


## 16.2 CNC-03 và CNC-04 thay thế


Cart chỉ cần qua một trong hai máy. Nếu CNC-03 gọi thì giao CNC-03; nếu CNC-04 gọi thì giao CNC-04. Nếu sau này muốn hệ thống tự chọn máy mà không có trạm gọi cụ thể, cần một luồng khác và dữ liệu trạng thái máy.


## 16.3 Khu tẩy rửa đầy


Nếu công đoạn cuối hoàn thành nhưng mọi slot đều bận, không gửi task vào slot bận. Cần nhà máy chốt: báo không có slot, giữ cart ở CNC cuối hay dùng buffer.


## 17. Lộ trình tiếp tục công việc


Chốt ba câu nghiệp vụ ảnh hưởng trực tiếp: đích cấp nguyên liệu; xử lý khi khu tẩy rửa đầy; định nghĩa điều kiện sửa route.

Lấy tài liệu API/Swagger và xác minh cơ chế lấy/thả cart.

Lập bảng từng luồng: sự kiện khởi tạo → điều kiện → pickup/drop-off → request FM → phản hồi → trạng thái → kết thúc.

Vẽ state machine riêng cho yêu cầu nội bộ, task FM và tiến độ sản xuất.

Xác định định danh cart và mapping giữa CNC/location nội bộ với node/location FM.

Thiết kế xử lý task trùng, timeout không rõ kết quả, FM reject, robot lỗi, nguồn hết xe, đích hết chỗ.

Sau khi nghiệp vụ/API rõ mới chốt database, backend endpoint, UI tablet và cập nhật realtime.

Dùng demo HTML để review thao tác, không coi demo là xác nhận kỹ thuật.


## 18. Prompt khởi đầu cho người/AI tiếp quản


Bạn đang tiếp quản một bài toán tích hợp AMR vào dây chuyền sản xuất. Hãy đọc toàn bộ tài liệu này trước khi đưa ra giải pháp. Trước tiên tóm tắt những gì đã xác nhận, những gì mới là định hướng và những gì còn mở. Không bịa API, payload, trạng thái hoặc khả năng vật lý của AMR. Không hỏi lại các thông tin đã xác nhận. Tiếp tục từng bước nhỏ: ưu tiên câu hỏi nghiệp vụ có ảnh hưởng tới thiết kế, rồi mới tới API và kiến trúc. Với mỗi đề xuất, nêu rõ giả định, lý do, rủi ro và quyết định cần người dùng/nhà máy/nhà cung cấp xác nhận.


## 19. Tài liệu liên quan


Tài liệu làm việc trước đó: “TÀI LIỆU NGHIỆP VỤ TÍCH HỢP AMR | BẢN LÀM VIỆC 0.1”.

Demo HTML: amr_integration_demo.html — mô phỏng nghiệp vụ, chưa tích hợp AMR thật.

Tài liệu tổng hợp trước: Tong_hop_nghiep_vu_tich_hop_AMR_ban_lam_viec.docx.

Nếu tài liệu cũ có chi tiết khác với bản này, đừng âm thầm chọn một bên; đối chiếu và hỏi người dùng nếu ảnh hưởng tới nghiệp vụ. Mọi mục 'cần xác minh' vẫn là câu hỏi mở.

## 20. Báo cáo Scan Toàn diện Database Hiện tại (30 Bảng) & Đánh giá Tái cấu trúc cho Kuka AMR

### 20.1 Phân tích Chuyên sâu về Đề xuất của User: Giữ Location, Tận dụng Item & ItemStock

#### 1. Đánh giá Bảng `location` (Quyết định: GIỮ NGUYÊN 100%)
* **Lý do**: Bảng `location` hiện tại đã được tích hợp hoàn chỉnh với `WarehouseMapCanvas` trên Frontend và chứa đầy đủ các trường vị trí: `location_code`, `location_name`, `bin_code`, `map_x`, `map_y`, `warehouse_id`, `zone_id`.
* **Kế hoạch**: Giữ nguyên toàn bộ cấu trúc bảng `location` để quản lý các vị trí trạm máy `CNC-01`..`CNC-05`, 7 vị trí cấp nguyên liệu và các slot khu tẩy rửa. Chỉ cần gỡ bỏ các ràng buộc/property tính toán tồn kho liên quan đến `ItemStock` và `InboundOrderDetail`.

#### 2. Đánh giá Tái sử dụng `item` làm Danh mục Model Sản phẩm (RẤT KHẢ THI - KHUYÊN DÙNG)
* **Ý tưởng**: Dùng bảng `item` đại diện cho các **Model sản phẩm** (ví dụ Model A, Model B...):
  * `sku` -> Mã Model (ví dụ `MODEL_A`).
  * `name` -> Tên Model (ví dụ `Trục khuỷu Model A`).
  * `description` -> Mô tả kỹ thuật.
  * `warehouse_id` -> Thuộc xưởng nào.
* **Cần điều chỉnh**: Cho phép `base_unit`, `max_quantity`, `min_quantity`, `supplier` chuyển sang dạng nullable hoặc set giá trị mặc định để không bắt buộc các trường WMS kho.

#### 3. Đánh giá Tái sử dụng `item_stock` làm Cart (Xe gá phôi / WIP)
* **Ưu điểm lớn**:
  * `item_stock` đã có sẵn liên kết tới `item_id` (Model sản phẩm) và `location_id` (vị trí hiện tại trên sơ đồ xưởng).
  * Đã có sẵn trường phục vụ sản xuất: `manufacturing_machine`, `manufacturing_user`, `qc_user`, `status`.
  * Frontend map canvas hiện tại đã sẵn sàng render các chấm tròn hiển thị xe/phôi dựa trên `location.stocks`.
* **Nhược điểm & Các điểm cần bổ sung bắt buộc (Refactor)**:
  * Cần thêm cột `cart_code` (mã định danh xe thực tế/RFID thay vì chỉ dùng UUID `stock_code`).
  * Cần thêm cột `last_completed_step_id` (bước công đoạn vừa hoàn thành ở CNC trước).
  * Cần thêm cờ `is_locked` / `locked_by_task_id` (phục vụ chống tranh chấp xe giữa 2 máy song song).
  * Gỡ bỏ các FK ràng buộc với WMS kho: `inbound_order_detail_id`, `unit_id`, `available_quantity` tính từ `OutboundOrderAllocation`.

---

### 20.2 Chi tiết Toàn bộ 30 Bảng Database Hiện tại

#### NHÓM 1: VỊ TRÍ, BẢN ĐỒ & KHU VỰC XƯỞNG (GIỮ LẠI & TẬN DỤNG CHÍNH)

##### 1. Bảng `location` (Vị trí trạm máy / Slot xưởng)
* **Các trường (Columns)**:
  * `id`: INTEGER [PK]
  * `location_code`: VARCHAR(50) (Not Null) - Mã node trên sơ đồ
  * `location_name`: VARCHAR(100) (Not Null) - Tên vị trí (CNC-01, Slot Nguyên liệu 1...)
  * `bin_code`: VARCHAR(50) (Nullable) - Mã định danh vật lý
  * `row`, `column`, `level`: VARCHAR(10) (Nullable) - Tọa độ kệ (nếu có)
  * `node_name`: VARCHAR(50) (Nullable) - Tên node phụ
  * `map_x`, `map_y`: INTEGER (Nullable) - Tọa độ 2D dùng vẽ canvas và tính khoảng cách Euclidean
  * `warehouse_id`: INTEGER -> FK(warehouse.id)
  * `zone_id`: INTEGER -> FK(zone.id)
  * `is_active`: BOOLEAN (Not Null)
  * `created_at`, `updated_at`: DATETIME
* **Chức năng hiện tại**: Quản lý tọa độ từng vị trí ô kệ/trạm trên sơ đồ mặt bằng xưởng.
* **Đánh giá**: **GIỮ NGUYÊN 100%**. Đây là xương sống để tính khoảng cách xe gần nhất và hiển thị layout 2D.

##### 2. Bảng `warehouse` (Nhà xưởng / Khu vực tổng)
* **Các trường**: `id` [PK], `code` VARCHAR(20), `name` VARCHAR(100), `description` TEXT.
* **Chức năng hiện tại**: Đại diện cho kho tổng.
* **Đánh giá**: **GIỮ NGUYÊN**. Đại diện cho Nhà xưởng KUKA.

##### 3. Bảng `zone` (Khu vực chức năng)
* **Các trường**: `id` [PK], `warehouse_id` -> FK(warehouse.id), `code` VARCHAR(20), `name` VARCHAR(100), `description` TEXT.
* **Chức năng hiện tại**: Phân vùng kho.
* **Đánh giá**: **GIỮ NGUYÊN**. Dùng phân loại: Khu nguyên liệu, Khu trạm máy CNC, Khu tẩy rửa.

##### 4. Bảng `warehouse_map` (Dữ liệu bản đồ import)
* **Các trường**: `id` [PK], `warehouse_id` -> FK(warehouse.id), `zone_id` -> FK(zone.id), `source` VARCHAR(255), `is_active` BOOLEAN, `created_at` DATETIME.
* **Chức năng hiện tại**: Lưu file nguồn map layout của xưởng.
* **Đánh giá**: **GIỮ NGUYÊN**. Phục vụ import bản đồ và cấu hình layout.

---

#### NHÓM 2: SẢN PHẨM & XE GÁ PHÔI (TẬN DỤNG & MỞ RỘNG)

##### 5. Bảng `item` (Danh mục sản phẩm / Model)
* **Các trường**:
  * `id`: INTEGER [PK]
  * `sku`: VARCHAR(50) (Not Null) - Dùng làm Mã Model (Model A, B,...)
  * `name`: VARCHAR(255) (Not Null) - Tên Model
  * `description`: TEXT
  * `base_quantity`: BIGINT (Default 1)
  * `base_unit`: INTEGER -> FK(unit.id)
  * `max_quantity`, `min_quantity`: INTEGER
  * `is_active`: BOOLEAN
  * `warehouse_id`: INTEGER -> FK(warehouse.id)
  * `details`: JSON
  * `supplier`: VARCHAR(50)
  * `created_at`, `updated_at`: DATETIME
* **Chức năng hiện tại**: Danh mục SKU sản phẩm trong kho.
* **Đánh giá**: **TÁI SỬ DỤNG LÀM BẢNG MODEL SẢN PHẨM**. Bỏ bắt buộc `base_unit` và `supplier`.

##### 6. Bảng `item_stock` (Xe gá phôi / Cart WIP)
* **Các trường**:
  * `id`: INTEGER [PK]
  * `stock_code`: UUID (Not Null)
  * `item_id`: INTEGER -> FK(item.id) (Model sản phẩm đang chở)
  * `location_id`: INTEGER -> FK(location.id) (Vị trí trạm máy xe đang đỗ)
  * `inbound_order_detail_id`: INTEGER -> FK (WMS cũ)
  * `unit_id`: INTEGER -> FK(unit.id)
  * `quantity`: NUMERIC(12, 3)
  * `lot_number_from`, `lot_number_to`, `expiry_date`: VARCHAR(50) (WMS cũ)
  * `status`: VARCHAR(20) (Trạng thái xe: available, in_transit, processing...)
  * `manufacturing_machine`: VARCHAR(50) (Máy vừa gia công)
  * `manufacturing_user`, `qc_user`, `packing_user`, `cavity_number`, `stock_level`: VARCHAR/INT
  * `is_active`: BOOLEAN, `created_at`, `updated_at`: DATETIME
* **Chức năng hiện tại**: Lưu tồn kho chi tiết tại từng ô vị trí.
* **Đánh giá**: **TÁI SỬ DỤNG VÀ NÂNG CẤP LÀM BẢNG CART/WIP**. Bổ sung trường `cart_code`, `last_completed_step_id`, `is_locked`. Bỏ các FK liên quan inbound order.

##### 7. Bảng `unit` (Đơn vị tính)
* **Các trường**: `id` [PK], `name` VARCHAR(100), `description` TEXT, `created_at`, `updated_at`.
* **Chức năng hiện tại**: Quản lý đơn vị (thùng, cái, cuộn...).
* **Đánh giá**: **GIỮ TỰ CHỌN** (đơn vị xe / cart / chi tiết), không còn là trọng tâm.

##### 8. Bảng `item_unit` (Chuyển đổi đơn vị)
* **Các trường**: `id` [PK], `item_id` -> FK, `unit_id` -> FK, `conversion_factor` NUMERIC(12,4).
* **Đánh giá**: **ĐẬP ĐI (DROP)**. Dây chuyền sản xuất tính theo chiếc/xe cart, không cần hệ số quy đổi thùng/hộp.

##### 9. Bảng `item_stock_relation` (Quan hệ phân tách lô tồn kho)
* **Các trường**: `id` [PK], `parent_stock_id` -> FK, `child_stock_id` -> FK, `relation_type` VARCHAR(50).
* **Đánh giá**: **ĐẬP ĐI (DROP)**. Phục vụ chia nhỏ pallet FMCG Masan, không dùng cho Cart cơ khí.

##### 10. Bảng `inventory_daily_snapshot` (Chụp ảnh tồn kho theo ngày)
* **Các trường**: `id` [PK], `warehouse_id` -> FK, `snapshot_date` DATE, `total_quantity`, `total_inventory_value`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**. Nghiệp vụ tài chính kho, không dùng cho dây chuyền KUKA.

---

#### NHÓM 3: ĐƠN HÀNG NHẬP / XUẤT KHO WMS MASAN (ĐẬP ĐI / LOẠI BỎ TOÀN BỘ)

##### 11. Bảng `inbound_order` (Lệnh nhập kho)
* **Các trường**: `id` [PK], `order_code`, `note`, `created_by_id`, `warehouse_id`, `details` JSON.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 12. Bảng `inbound_order_detail` (Chi tiết nhập kho)
* **Các trường**: `id` [PK], `inbound_order_id`, `from_location_id`, `to_location_id`, `details`, `status`, `detail_type`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 13. Bảng `inbound_order_allocation` (Phân bổ vị trí nhập)
* **Các trường**: `id` [PK], `inbound_order_detail_id`, `item_stock_id`, `unit_id`, `quantity`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 14. Bảng `outbound_order` (Lệnh xuất kho)
* **Các trường**: `id` [PK], `order_code`, `note`, `created_by_id`, `warehouse_id`, `details` JSON.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 15. Bảng `outbound_order_detail` (Chi tiết xuất kho)
* **Các trường**: `id` [PK], `outbound_order_id`, `item_id`, `quantity`, `unit`, `detail_type`, `details`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 16. Bảng `outbound_order_allocation` (Phân bổ xuất kho và gán Robot)
* **Các trường**: `id` [PK], `outbound_order_detail_id`, `item_stock_id`, `quantity`, `status`, `from_location_id`, `to_location_id`, `allocation_type`, `robot_task_id`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 17. Bảng `transaction` (Giao dịch chuyển vị trí hàng)
* **Các trường**: `id` [PK], `from_location_id`, `to_location_id`, `transaction_type`, `item_stock_id`, `quantity`, `created_by_id`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**. Thay bằng bảng `production_record` và `fleet_task`.

##### 18. Bảng `history` (Lịch sử trạng thái đơn hàng)
* **Các trường**: `id` [PK], `inbound_order_id`, `outbound_order_id`, `old_status`, `new_status`, `created_by_id`, `description`, `details`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 19. Bảng `qr_code` (Mã QR in dán thùng hàng Masan)
* **Các trường**: `id` [PK], `code`, `item_id`, `item_stock_id`, `qr_type`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

---

#### NHÓM 4: KIỂM KÊ KHO WMS (ĐẬP ĐI)

##### 20. Bảng `stocktake` (Phiếu kiểm kê)
* **Các trường**: `id` [PK], `warehouse_id`, `created_by_id`, `description`, `created_at`, `updated_at`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

##### 21. Bảng `stocktake_item` (Chi tiết kiểm đếm kho)
* **Các trường**: `id` [PK], `stocktake_id`, `item_stock_id`, `lot_number`, `location_id`, `desired_quantity`, `actual_quantity`, `status`.
* **Đánh giá**: **ĐẬP ĐI (DROP)**.

---

#### NHÓM 5: ROBOT TASK & TÍCH HỢP FLEET (REFACTOR THÀNH FLEET ADAPTER)

##### 22. Bảng `robot_task` (Lệnh gọi robot cũ của Hikrobot/ICS)
* **Các trường**:
  * `id`: INTEGER [PK]
  * `inbound_order_detail_id`: INTEGER -> FK (bị dính cứng với đơn nhập kho cũ)
  * `order_id`: VARCHAR(50) (Not Null)
  * `quantity`: INTEGER (Not Null)
  * `process_code`: VARCHAR(50) (Not Null)
  * `system_code`: VARCHAR(50) (Not Null)
  * `task_order_detail`: VARCHAR(255) (Not Null)
  * `created_at`: DATETIME
* **Chức năng hiện tại**: Gửi task sang hệ thống Hikrobot ICS.
* **Đánh giá**: **REFACTOR THÀNH `fleet_task`**. Bỏ liên kết `inbound_order_detail_id`, gắn trực tiếp với `transport_request_id`, lưu điểm lấy `pickup_location_id` và điểm thả `dropoff_location_id`.

##### 23. Bảng `task_status` (Trạng thái callback từ robot)
* **Các trường**: `id` [PK], `sub_task_status`, `order_id`, `device_code`, `device_num`, `qr_code`, `shelf_number`, `status`.
* **Chức năng hiện tại**: Nhận webhook cập nhật trạng thái từ robot.
* **Đánh giá**: **TẬN DỤNG & ĐỒNG BỘ VÀO `fleet_task`**.

---

#### NHÓM 6: XÁC THỰC, TÀI KHOẢN & PHÂN QUYỀN (GIỮ NGUYÊN 100%)

##### 24. Bảng `users`: `id` [PK], `username`, `email`, `hashed_password`, `is_active`, `created_at`, `updated_at`. -> **GIỮ NGUYÊN**
##### 25. Bảng `roles`: `id` [PK], `name`, `description`. -> **GIỮ NGUYÊN**
##### 26. Bảng `permissions`: `id` [PK], `code`, `name`, `module`, `description`. -> **GIỮ NGUYÊN**
##### 27. Bảng `user_roles`: `user_id` [PK], `role_id` [PK]. -> **GIỮ NGUYÊN**
##### 28. Bảng `user_warehouses`: `user_id` [PK], `warehouse_id` [PK]. -> **GIỮ NGUYÊN**
##### 29. Bảng `role_permissions`: `role_id` [PK], `permission_id` [PK]. -> **GIỮ NGUYÊN**

---

#### NHÓM 7: HỆ THỐNG CẢNH BÁO (GIỮ NGUYÊN)

##### 30. Bảng `notification`: `id` [PK], `warehouse_id`, `title`, `message`, `action`, `notification_type`, `status`. -> **GIỮ NGUYÊN**.

---

### 20.3 Các Bảng MỚI cần bổ sung cho Hệ thống Dây chuyền KUKA AMR

Để hoàn thiện dây chuyền điều phối KUKA AMR mà không làm xáo trộn các bảng cốt lõi giữ lại:
1. **`production_route`**: Quản lý quy trình route theo Model (`id`, `item_id` -> FK(item.id), `route_name`, `version`, `is_active`).
2. **`route_step`**: Các bước gia công trong route (`id`, `route_id`, `step_order`, `step_name`, `location_id` -> hỗ trợ nhóm máy thay thế như CNC-03 OR CNC-04).
3. **`transport_request`**: Quản lý yêu cầu gọi xe của công nhân trên tablet (`id`, `request_code`, `destination_location_id`, `item_id`, `cart_stock_id`, `status`).
4. **`transport_queue`**: Hàng đợi tự động (Quản lý hàng đợi khi máy CNC chờ xe sẵn sàng, hoặc xe chờ slot khu tẩy rửa).
5. **`fleet_task`**: Quản lý task gửi sang Fleet Manager KUKA/AMR (`id`, `transport_request_id`, `fm_task_id`, `pickup_location_id`, `dropoff_location_id`, `status`).
6. **`production_record`**: Lịch sử công nhân bấm xác nhận hoàn thành công đoạn gia công tại từng trạm máy.


## 21. Đặc tả Chi tiết Thiết bị, Giao diện PDA 4.2 Inch & UX Vận hành

### 21.1 Phân định Thiết bị (Device Form Factor)
- **Giao diện Admin / Quản trị viên**: Chạy trên **MÁY TÍNH (Desktop / PC)** với màn hình lớn, đầy đủ thanh điều hướng, bảng danh sách quản lý, cấu hình Route, sơ đồ 2D canvas toàn cảnh xưởng và phân quyền trạm máy cho User.
- **Giao diện User / Operator (Công nhân xưởng)**: Chạy trên **PDA CẦM TAY 4.2 INCH** (màn hình dọc ~480x800px).
  - Không có thanh Menu / Sidebar điều hướng phức tạp.
  - Người dùng vào thẳng giao diện trạm máy của mình (Modal-first / App-like).
  - Các nút bấm cảm ứng cực to (chiều cao >= 52px), bo góc, tương phản cao để thao tác bằng 1 ngón cái hoặc khi đeo găng tay bảo hộ.

### 21.2 Quy tắc Hộp thoại Xác nhận (Confirmation Dialogs - Bắt buộc)
Do môi trường xưởng thao tác nhanh và có thể đeo găng tay, **mọi hành động quan trọng đều phải có Popup xác nhận** trước khi gửi lệnh xuống hệ thống:
1. **Khu Nguyên liệu**: Sau khi chọn vị trí, model và quét QR -> Hiện popup xác nhận thông tin trước khi lưu.
2. **Khu CNC - Gọi xe**: Bấm vào vị trí trống để gọi hàng -> Hiện popup: *'Bạn có chắc chắn muốn gọi [Model X] về vị trí [CNC-YY] không?'* [Xác nhận] [Hủy].
3. **Khu CNC - Hoàn thành công đoạn**: Bấm vào vị trí có hàng để Update Level -> Hiện popup: *'Xác nhận đã gia công xong và nâng lên Level [Z] cho Rack [Mã Rack]?'* [Xác nhận] [Hủy].
4. **Khu Tẩy rửa - Giải phóng slot**: Bấm vào vị trí đầy -> Hiện popup: *'Xác nhận đã lấy Rack [Mã Rack] đi rửa và giải phóng [Slot W]?'* [Xác nhận] [Hủy].

### 21.3 Luồng Wizard 3 Bước Tuần tự tại Khu Nguyên Liệu (3 Màn hình riêng biệt)
Để màn hình PDA 4.2 inch không bị quá tải thông tin và tránh bấm nhầm:
- **Màn hình 1 (Chọn Vị trí)**: Hiển thị 7 nút to bản tương ứng 7 vị trí (VT-01 đến VT-07). Công nhân bấm chọn 1 vị trí -> Tự động chuyển sang Màn hình 2.
- **Màn hình 2 (Chọn Model)**: Hiển thị danh sách các Model sản phẩm (Model 1 đến Model 7). Bấm chọn Model -> Tự động chuyển sang Màn hình 3. (Có nút [Quay lại] để đổi vị trí).
- **Màn hình 3 (Quét QR Rack)**: Ô hiển thị mã Rack kèm nút kích hoạt camera quét QR hoặc nhận tín hiệu từ phím cứng scan của PDA.
  - Sau khi quét được mã Rack -> Bật Popup xác nhận: *'Xác nhận nạp [Model X] vào [Rack ID] tại [Vị trí Y]?'*.
  - Bấm [Xác nhận] -> Hoàn tất và quay về Màn hình 1 sẵn sàng cho lần nạp tiếp theo.
