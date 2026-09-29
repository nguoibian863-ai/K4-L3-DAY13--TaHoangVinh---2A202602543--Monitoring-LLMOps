# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.txt` hoặc `evidence/11-dashboard-overview.png`.

## 1. Thông tin học viên

- **Họ và tên:** Tạ Hoàng Vinh
- **MSSV:** 2A202602543
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/nguoibian863-ai/K4-L3-DAY13--TaHoangVinh---2A202602543--Monitoring-LLMOps
- **Commit SHA cuối:** `565d556d5d5690d7e1dd5b5665ed3962c6d8cfa7`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (Cohort K4, seed 1311, feature: `monitoring`)
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602543` (Project ID: `cmumdr2aa20yrad0d9djqhuc4`)

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100; thiếu required fields/enrichment và correlation ID | 100/100 | Đạt toàn bộ JSON schema, context enrichment, correlation ID và PII scrubbing |
| `validate_dashboard.py` | Hợp lệ 6/6 panel | Hợp lệ 6/6 panel | Dashboard runtime tại `/dashboard` đầy đủ 6/6 panels contract |
| `pytest` | 22 passed in 2.17s | 25 passed in 1.44s | Hoàn thành 100% test suite tự động |
| Số traces hợp lệ | 0 | 11 traces | 11 traces phân cấp đầy đủ quan sát trong project Langfuse cá nhân |
| Số PII leak | 0 | 0 | Validator xác nhận 0 leak, che toàn bộ Email, Phone VN, CCCD, Thẻ ngân hàng |
| Latency P95 / TTFT P95 | 150 ms / 50 ms | 152 ms / 50 ms | Cửa sổ dashboard 60 phút ở trạng thái chuẩn |
| Retrieval success rate | 100% | 100% | Theo trường `tool_success` trong structured log |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Trong [`app/middleware.py`](../app/middleware.py), middleware `CorrelationIdMiddleware` tiếp nhận header `x-request-id` từ request. Nếu chưa có hoặc sai định dạng `req-<8-hex>`, middleware tự động sinh mới với mẫu `req-{uuid4().hex[:8]}`. Trước khi gọi xử lý tiếp, middleware gọi `clear_contextvars()` để tránh ô nhiễm context từ request trước, sau đó bind `correlation_id` vào request state và contextvars. Response trả về được gán header `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:**
  Trong [`app/main.py`](../app/main.py), các metadata bắt buộc được bind gồm `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model`, `env` (APP_ENV), `correlation_id`, `service="api"`. Ở sự kiện `response_sent`, ghi nhận thêm các chỉ số hiệu năng và tool: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name="retrieval"`, `tool_success=True`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  Trong [`app/logging_config.py`](../app/logging_config.py), processor `scrub_pii_processor` được đăng ký đứng trước renderer JSON và file writer. Processor này duyệt đệ quy qua toàn bộ các trường dữ liệu và gọi `scrub_text` trong [`app/pii.py`](../app/pii.py). Mọi thông tin nhạy cảm (Email, Số điện thoại Việt Nam các mạng Viettel/Vina/Mobi..., CCCD 12 số, Thẻ tín dụng/ghi nợ) đều được thay bằng token `[REDACTED_*]` trước khi ghi xuống đĩa hoặc ra terminal.
- **Cách kiểm chứng kết quả:**
  Chạy `python scripts/validate_logs.py` đạt điểm số 100/100, xác nhận không còn bất kỳ PII thô nào trong `data/logs.jsonl`; đồng thời vượt qua toàn bộ các ca kiểm thử trong `tests/test_pii.py`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Traces được đẩy trực tiếp lên project Langfuse Cloud cá nhân mang tên `day13-k4-l3a-2A202602543` (Project ID: `cmumdr2aa20yrad0d9djqhuc4`), sử dụng API key cá nhân được cấu hình trong `.env`. Xác nhận thông qua việc query trực tiếp Langfuse API (`client.api.observations.get_many`) ghi nhận 11 traces phân cấp do chính tài khoản tạo, gắn tag `["lab", "api", feature]` và user_id_hash tương ứng.
- **Cấu trúc root/retrieval/generation observations:**
  Mỗi trace bao gồm cây quan sát phân cấp:
  1. Root Observation: `process-chat-request` (loại `agent`) theo dõi toàn bộ vòng đời xử lý của request.
  2. Child Observation 1: `retrieve-context` (loại `retriever`) theo dõi quá trình truy vấn tài liệu, ghi nhận `doc_count` và các tài liệu tham khảo đã scrub PII.
  3. Child Observation 2: `generate-response` (loại `generation`) theo dõi bước gọi mô hình ngôn ngữ sinh kết quả, liên kết trực tiếp với managed prompt, mô hình `claude-sonnet-4-5`, chi tiết usage (`input_tokens`, `output_tokens`) và cost.
- **Cách nối trace với log:**
  Dùng chung mã `correlation_id`. Trong code agent, `correlation_id` được truyền vào `propagate_attributes(metadata={"correlation_id": correlation_id})` và span metadata của Langfuse. Nhờ đó, từ một log record bất thường có thể lập tức tra cứu chính xác trace tương ứng trên giao diện Langfuse.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, gắn nhãn `['baseline', 'production']`.
- **Version/label candidate:** Version 2, gắn nhãn `['candidate']`.
- **Trace ID của mỗi version:**
  - Version 1 (baseline/production): Trace `49307985bd5a30c7a460693c6d961f7f`
  - Version 2 (candidate): Trace `b1b284419abdf6fa92a1784687ec71ca`
- **Cách promote và rollback `production`:**
  - Promote: Chuyển label `production` sang Version 2 qua `client.update_prompt(name='day13-chat', version=2, new_labels=['candidate', 'production'])`. Ứng dụng khi chạy với `LANGFUSE_PROMPT_LABEL=production` sẽ tự động tải prompt Version 2.
  - Rollback: Khi cần hoàn tác, gọi `client.update_prompt(name='day13-chat', version=1, new_labels=['baseline', 'production'])` và gỡ nhãn khỏi Version 2 `client.update_prompt(name='day13-chat', version=2, new_labels=['candidate'])`. Hệ thống phục hồi ngay về Version 1 mà không cần sửa code hay khởi động lại service.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  FastAPI route `/dashboard` render trực tiếp từ `data/logs.jsonl` trong cửa sổ 60 phút với cơ chế auto-refresh 30 giây. Đúng 6 panel theo chuẩn: (1) Latency & TTFT (P50, P95, P99, TTFT), (2) Traffic (requests/phút), (3) Errors & Retrieval Success Rate, (4) Cost, (5) Tokens (Input vs Output), và (6) Quality score distribution. Evidence: `evidence/11-dashboard-overview.png`.
- **SLO và lý do chọn:**
  Cam kết 99.5% request hoàn tất (`response_sent`) có latency không vượt quá 3000 ms trong chu kỳ 28 ngày. Baseline P95 ở mức ~152 ms, ngưỡng 3000 ms vừa đủ bao dung các biến động mạng/tài nguyên thông thường nhưng lập tức phát hiện các tình trạng suy thoái hiệu năng mà người dùng bắt đầu khó chịu.
- **Cách tính error budget:**
  Với SLO 99.5%, Error Budget cho phép là `100% - 99.5% = 0.5%`. Tương ứng số request vượt ngưỡng hoặc lỗi tối đa là `total_requests × 0.005`. Theo thời gian, trong chu kỳ 28 ngày: `28 ngày × 24 giờ × 60 phút × 0.5% = 201.6 phút downtime/degradation`.
- **Ba alert và runbook tương ứng:**
  - High user-visible latency: Kích hoạt khi `P95 latency > 3000 ms` kéo dài liên tục 5 phút. Kênh: `#llmops-alerts`. Runbook hướng dẫn kiểm tra upstream/downstream và chuyển sang fallback mode.
  - Elevated request failures: Kích hoạt khi `error rate > 2%` kéo dài liên tục 5 phút. Kênh: `#llmops-alerts`. Runbook hướng dẫn tra cứu log lỗi `request_failed` và kiểm tra dịch vụ phụ thuộc.
  - Degraded answer quality: Kích hoạt khi `quality score mean < 0.75` kéo dài 10 phút. Kênh: `#llmops-alerts`. Runbook hướng dẫn rà soát prompt version gần nhất và rollback về baseline nếu cần. Chi tiết xem tại [`docs/alerts.md`](../docs/alerts.md).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (Cohort K4, Seed: 1311, Affected Feature: `monitoring`, Latency Threshold: 2000 ms).
- **Khoảng thời gian điều tra:** 2026-09-29 09:33:55Z – 09:34:11Z.
- **Triệu chứng từ metrics:** P95 latency tăng đột biến lên 4630 ms (P99: 4644 ms, P50: 2652 ms); trong khi đó TTFT P95 hoàn toàn không đổi ở 50 ms. Chỉ số này vi phạm nghiêm trọng ngưỡng cam kết SLO P95 <= 3000 ms. Đồ thị latency trên dashboard vọt đỉnh trong khi các chỉ số error rate (0%) và retrieval success (100%) giữ nguyên. Evidence: `evidence/12-incident-metric.png`.
- **Log line và correlation ID liên quan:**
  Sự kiện `response_sent` lúc `2026-09-29T09:34:01.143938Z`, `latency_ms=4623`, `ttft_ms=50`, `correlation_id=req-9ca8cb8c`, `feature="monitoring"`, `user_id_hash="dc9b2ec8da9d"`, `session_id="k4-l3a-challenge-s03"`, `model="claude-sonnet-4-5"`. Evidence: `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:**
  Khớp correlation ID `req-9ca8cb8c` với Trace ID `cff3631f96301531892cec0f3270deeb` trên project Langfuse cá nhân `day13-k4-l3a-2A202602543`. Cây phân cấp thời gian cho thấy:
  - Root Observation: `process-chat-request` (Total: 2.653s)
  - Child Span 1: `retrieve-context` (Duration: 2.501s, chiếm 94% tổng thời gian request) -> **ĐÂY LÀ BƯỚC NGHẼN NGUYÊN NHÂN**
  - Child Span 2: `generate-response` (Duration: 0.152s, hoàn toàn bình thường)
  Evidence: `evidence/14-incident-trace.png`.
- **Root cause:** Module tìm kiếm tài liệu `mock_rag` trong bước retrieval bị chèn delay nhân tạo (kịch bản `rag_slow`) cho các request liên quan đến feature `monitoring`, khiến bước retrieval tốn hơn 2.5 giây, kéo dãn tail latency của toàn bộ pipeline trước khi bước generation được thực thi.
- **Fix action:** Vô hiệu hóa kịch bản incident bằng `python scripts/inject_incident.py --disable` (hoặc `POST /incidents/rag_slow/disable`). Kiểm tra lại endpoint `/health` xác nhận `incidents: {"rag_slow": false, ...}`.
- **Preventive measure:**
  1. Cấu hình Alert P95 latency > 3000 ms trong 5 phút để kích hoạt thông báo P1 cho on-call.
  2. Bổ sung timeout (ví dụ 1.5s) kèm circuit breaker cho bước retrieval để ngắt sớm và dùng cached context nếu downstream bị chậm.
  3. Bổ sung panel theo dõi riêng retrieval duration trên dashboard để lập tức phân biệt độ trễ do retrieval hay do LLM generation.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Tách riêng biệt các span con (`retrieve-context` dạng retriever và `generate-response` dạng generation) trong một root observation thống nhất thay vì coi agent là một khối đen (black box). Quyết định này là mấu chốt giúp xác định ngay lập tức nguyên nhân chậm nằm ở bước lấy dữ liệu hay ở mô hình ngôn ngữ khi có incident xảy ra.
- **Một lỗi/blocker đã gặp:**
  Trong quá trình khởi chạy ban đầu, cổng 8000 bị một tiến trình server cũ chiếm giữ, đồng thời kết nối xuất trace sang Langfuse Cloud gặp lỗi timeout do độ trễ mạng Internet cục bộ.
- **Cách tìm nguyên nhân và xử lý:**
  Sử dụng lệnh PowerShell kiểm tra tiến trình theo PID đang giữ cổng để kill triệt để; sau đó kiểm tra xác thực bằng `auth_check()`, tăng timeout truy vấn lên 25s và bảo đảm gọi `flush_traces()` đầy đủ.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - Metrics (Tầng vĩ mô): Chỉ ra *Có vấn đề gì đang xảy ra và xảy ra khi nào* (ví dụ: P95 latency tăng vọt từ 150ms lên 2650ms).
  - Logs (Tầng định danh): Chỉ ra *Request cụ thể nào bị ảnh hưởng*, cung cấp `correlation_id`, tham số đầu vào và ngữ cảnh môi trường.
  - Traces (Tầng vi mô): Chỉ ra *Tại sao và bước nào bên trong gây ra lỗi*, phân rã thời gian và payload của từng span độc lập.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  Quản trị prompt có version và nhãn độc lập giúp kiểm soát câu trả lời của AI như một artifact có phiên bản; theo dõi token/cost giúp tránh vượt ngân sách hoặc bẫy lặp token; SLO định lượng ranh giới trải nghiệm người dùng; và rollback là lá chắn an toàn tối thượng giúp phục hồi dịch vụ ngay lập tức khi bản cập nhật mới có vấn đề.
- **Điều quan trọng nhất đã học:**
  Kỹ năng xây dựng hệ thống quan sát đa tầng (Full-stack Observability) chuẩn mực cho AI Agents: từ bảo mật PII, quản trị metadata, đến liên kết chặt chẽ ba trụ cột Metrics - Logs - Traces.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Chờ file challenge riêng từ Lab Coach để nạp vào `config/challenge.json`; toàn bộ kiến trúc, mã nguồn và quy trình điều tra đã sẵn sàng 100%.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
