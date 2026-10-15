CONTEXT CHUYỂN GIAO DỰ ÁN
TÍCH HỢP AMR VÀO DÂY CHUYỀN SẢN XUẤT

Bản bàn giao chi tiết cho người mới tiếp quản / AI khác

Phiên bản 1.2 | Cập nhật ngày 15/10/2026 (Chốt 5 câu hỏi nghiệp vụ Grill & Báo cáo Scan Database)

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

## 20. Báo cáo Scan Database hiện tại & Kế hoạch Tái cấu trúc Schema Kuka AMR

### 20.1 Hiện trạng Database WMS cũ (Cần loại bỏ / Đập đi)
Codebase hiện tại là WMS quản lý kho thương mại/FMCG Masan, phụ thuộc vào các bảng không phù hợp với dây chuyền sản xuất:
- Nhập/Xuất kho: inbound_order, inbound_order_detail, inbound_order_allocation, outbound_order, outbound_order_detail, outbound_order_allocation.
- Quản lý tồn kho & Lô hàng: item_stock (quản lý pallet, lot number, hạn sử dụng, số lượng tồn, phân tách lô).
- Danh mục sản phẩm WMS: item, unit, item_unit (SKU hàng hóa thương mại).
- Kiểm kê kho: stocktake, stocktake_detail.
- Lịch sử kho: transaction, history, inventory_daily_snapshot.
- Bảng phụ: qr_code, item_import_staging_*.
- Robot Task cũ: robot_task (bị gắn chặt với inbound_order_detail_id và outbound_order_allocation).

### 20.2 Các bảng Tận dụng & Giữ lại
- Auth & RBAC: user, role, permission, user_warehouses.
- Phân vùng xưởng: warehouse, zone (đại diện cho các khu vực: Khu nguyên liệu, Khu CNC, Khu tẩy rửa).
- Trạm máy / Vị trí: location -> Tinh gọn thành station (giữ location_code, map_x, map_y, zone_id, warehouse_id, lược bỏ các quan hệ WMS phức tạp với ItemStock).
- Thông báo: notification.

### 20.3 Các bảng MỚI cần thiết kế cho Dây chuyền KUKA AMR
1. product_model: Quản lý danh mục model sản phẩm (Model A, B,...).
2. production_route: Quản lý quy trình route theo từng model.
3. route_step: Các bước công đoạn theo thứ tự (hỗ trợ nhóm máy song song/thay thế ví dụ CNC-03 OR CNC-04).
4. cart: Xe gá phôi (mã xe, model hiện tại, trạm hiện tại, bước vừa hoàn thành, trạng thái khóa, task đang chiếm giữ).
5. transport_request: Yêu cầu gọi xe từ tablet của công nhân.
6. fleet_task: Task điều phối gửi sang Fleet Manager (lưu task_id từ FM, request/response payload, trạng thái FM, timestamp).
7. transport_queue: Hàng đợi điều phối tự động (lưu các trạm đang chờ xe hoặc các xe đang chờ slot tẩy rửa, background task liên tục quét map để giải phóng queue).
8. production_record: Lịch sử công nhân bấm xác nhận hoàn thành công đoạn tại trạm.
